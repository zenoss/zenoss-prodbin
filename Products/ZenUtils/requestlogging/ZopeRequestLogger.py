#!/usr/bin/env python

import logging, logging.handlers 
import re
import os
import redis
import json
import time
import threading

from AccessControl import getSecurityManager
from Products.ZenUtils.RedisUtils import parseRedisUrl
from Products.ZenUtils.config import ConfigFile

class ZopeRequestLogger(object):
    """
    Logs information about the requests proccessed by Zopes.
    Disabled by default. It is enabled only when the file /opt/zenoss/etc/LOG-ZOPE-REQUESTS exists.
    """

    # SEPARATOR and FIELDS are used by a external tool
    SEPARATOR = '@$@'
    FIELDS = []
    FIELDS.append('user_name')
    FIELDS.append('start_time')
    FIELDS.append('end_time')
    FIELDS.append('duration')
    FIELDS.append('server_name')
    FIELDS.append('server_port')
    FIELDS.append('path_info')
    FIELDS.append('action_and_method')
    FIELDS.append('client')
    FIELDS.append('http_host')
    FIELDS.append('http_method')
    FIELDS.append('xff')
    FIELDS.append('body')

    FINGERPRINT_FIELDS = [ f for f in FIELDS if f not in ['end_time', 'duration', 'body', 'xff'] ]

    ACTION_REGEX = '"action":"(.+?)"'
    METHOD_REGEX = '"method":"(.+?)"'

    ZENHOME = os.environ.get('ZENHOME')
    DEFAULT_LOG_FILE = os.path.join(ZENHOME, 'log', 'ZReq.log')

    DEFAULT_REDIS_URL = 'redis://localhost:6379/0'
    REDIS_KEY_PATTERN = 'ZOPE-REQUEST'
    REDIS_LOG_ZOPE_REQUESTS = 'ZOPE-LOG-REQUESTS'

    REDIS_RECONNECTION_INTERVAL = 60

    MIN_REQUEST_DURATION = 5 # only requests that take more than MIN_REQUEST_DURATION seconds will be logged

    LOG = logging.getLogger('ZenUtils.ZopeRequestLogger')

    @staticmethod
    def create_redis_client(redis_url):
        client = None
        try:
            client = redis.StrictRedis(**parseRedisUrl(redis_url))
            client.config_get() # test the connection
        except Exception as e:
            client = None
            print e
        return client

    GLOBAL_CONF_SETTINGS = None

    @staticmethod
    def load_global_conf_settings():
        global_config_path = os.path.join(ZopeRequestLogger.ZENHOME, 'etc', 'global.conf')
        with open(global_config_path, 'r') as fp:
            global_conf = ConfigFile(fp)
            settings = {}
            for line in global_conf.parse():
                if line.setting:
                    key, val = line.setting
                    settings[key] = val
            ZopeRequestLogger.GLOBAL_CONF_SETTINGS = settings

    @staticmethod
    def get_redis_url():
        url = ZopeRequestLogger.DEFAULT_REDIS_URL
        if ZopeRequestLogger.GLOBAL_CONF_SETTINGS is None:
            ZopeRequestLogger.load_global_conf_settings()
        if ZopeRequestLogger.GLOBAL_CONF_SETTINGS.get('redis-url'):
            url = ZopeRequestLogger.GLOBAL_CONF_SETTINGS.get('redis-url')
        return url

    @staticmethod
    def get_request_min_duration():
        min_duration = ZopeRequestLogger.MIN_REQUEST_DURATION
        if ZopeRequestLogger.GLOBAL_CONF_SETTINGS is None:
            ZopeRequestLogger.load_global_conf_settings()
        if ZopeRequestLogger.GLOBAL_CONF_SETTINGS.get('log-requests-longer-than'):
            min_duration = ZopeRequestLogger.GLOBAL_CONF_SETTINGS.get('log-requests-longer-than')
        return int(min_duration)

    def __init__(self, filename = DEFAULT_LOG_FILE):
        self._next_config_check = time.time()
        self._log_zope_requests = False
        self._log = None
        self._redis_client = None
        self._redis_last_connection_attemp = time.time()
        self.redis_url = ZopeRequestLogger.get_redis_url()
        self._redis_client = ZopeRequestLogger.create_redis_client(self.redis_url)
        if not self._redis_client:
            ZopeRequestLogger.LOG.warn('ERROR connecting to redis. redis URL: {0}'.format(self.redis_url))
            ZopeRequestLogger.LOG.warn("Please check the redis-url value in global.conf")
        self._log = logging.getLogger('zope_request_logger')
        self._log.propagate = False
        handler = logging.handlers.RotatingFileHandler(filename, mode='a', maxBytes=50*1024*1024, backupCount=5)
        #handler = logging.handlers.TimedRotatingFileHandler(filename, when='midnight', backupCount=3)
        handler.setFormatter(logging.Formatter("%(asctime)s{0}%(message)s".format(ZopeRequestLogger.SEPARATOR)))
        self._log.addHandler(handler)
    
    def _extract_action_and_method_from_body(self, body):
        if body is None:
            return ''
        my_regex = re.compile(ZopeRequestLogger.ACTION_REGEX)
        actions = my_regex.findall(body)
        my_regex = re.compile(ZopeRequestLogger.METHOD_REGEX)
        methods = my_regex.findall(body)
        data = []
        for action, method in zip(actions, methods):
            data.append('({0},{1})'.format(action, method))
        return ''.join(data)

    def _load_data_to_log(self, request):
        '''
        return a dict containing the request data that is relevant for logging purposes
        '''
        if hasattr(request, '_data_to_log'):
            return

        data = {}
        user_name = getSecurityManager().getUser().getId()
        data['user_name'] = str(user_name)
        data['http_host'] = request.get('HTTP_HOST', default='')
        data['server_name'] = request.get('SERVER_NAME', default='')
        data['server_port'] = request.get('SERVER_PORT', default='')
        data['path_info'] = request.get('PATH_INFO', default='')
        data['action_and_method'] = ''
        data['body'] = request.get('BODY', {})
        data['action_and_method'] = self._extract_action_and_method_from_body(request.get('BODY'))
        data['client'] = request.get('REMOTE_ADDR', default='')
        data['start_time'] = str(request._start)
        data['http_method'] = request.get('method', default='')
        data['xff'] = request.get('X_FORWARDED_FOR', default='')
        try:
            ident = str(threading.current_thread().ident)
            fingerprint = ":".join((
                ZopeRequestLogger.REDIS_KEY_PATTERN,
                os.environ.get("CONTROLPLANE_SERVICED_ID", "X"),
                os.environ.get("CONTROLPLANE_INSTANCE_ID", "X"),
                str(os.getpid()),
                ident,
            ))
            request._store_fingerprint = fingerprint
            request._data_to_log = data
            request._user_name = user_name
        except Exception as ex:
            print ex

    def _reconnect_to_redis(self):
        now = time.time()
        if now - self._redis_last_connection_attemp > ZopeRequestLogger.REDIS_RECONNECTION_INTERVAL:
            ZopeRequestLogger.LOG.info("Trying to reconnect to redis")
            self._redis_last_connection_attemp = now
            self._redis_client = ZopeRequestLogger.create_redis_client(self.redis_url)
            if self._redis_client:
                ZopeRequestLogger.LOG.info("Connected to redis")
            else:
                ZopeRequestLogger.LOG.info("Could not connect to redis")

    def log_request(self, request, finished=False):
        ''' '''
        if self._redis_client is None:
            # Tries to reconnect to redis if we dont have a connection
            self._reconnect_to_redis()

        if self._redis_client:
            try:  # Tests the redis connection
                self._redis_client.config_get()
            except Exception as ex:
                ZopeRequestLogger.LOG.error("Connection to redis lost: %s", ex)
                self._redis_client = None
            else:
                if self._next_config_check <= time.time():
                    # self._log_zope_requests = self._redis_client.get(ZopeRequestLogger.REDIS_LOG_ZOPE_REQUESTS) in ("1", "true", "True", "t")
                    self._log_zope_requests = os.path.isfile(os.path.join(ZopeRequestLogger.ZENHOME, 'etc', ZopeRequestLogger.REDIS_LOG_ZOPE_REQUESTS))
                    self._next_config_check = time.time() + 10 # set next time to check in 10 seconds
                if not self._log_zope_requests:
                    return
                self._load_data_to_log(request)
                redis_key = request._store_fingerprint
                if finished and self._redis_client.exists(redis_key): #delete request from redis
                    self._redis_client.delete(redis_key)
                elif request._user_name : #write request to redis
                    redis_value = json.dumps(request._data_to_log)
                    self._redis_client.set(redis_key, redis_value)
                    self._redis_client.expire(redis_key, 24*60*60) # Keys expires after 24 hours
        if self._log and finished:
            self._load_data_to_log(request)
            ts = time.time()
            duration = ts - request._start
            if duration >= ZopeRequestLogger.get_request_min_duration():
                data_to_log = request._data_to_log
                data_to_log['end_time'] = str(ts)
                data_to_log['duration'] = str(duration)
                self._log.info(json.dumps(data_to_log))

