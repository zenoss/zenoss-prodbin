#!/usr/bin/env python

import logging
import re
import os
import redis
import json
import time
import threading

from AccessControl import getSecurityManager
from Products.ZenUtils.config import ConfigFile
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.ZenUtils.RedisUtils import parseRedisUrl

log = logging.getLogger('ZenUtils.ZopeRequestLogger')

class ZopeRequestLogger(object):
    """
    Logs information about requests proccessed by Zopes. Disabled by default. Two types of logging:

        1 - Request duration metrics are pushed to opentsdb when a request finishes if
          its duration is higer than a configurable parameter. This logging is enabled by
          setting "zope-request-logging" in global.conf to a value greater
          than zero. The value represents the min duration of requests to be logged.
          It must be > 0, otherwise we would log too much

        2 - Requests that started and have not yet finished. This logging is enabled by running
            "zencheckzopes enable"
    """

    FIELDS = []
    FIELDS.append('user_name')
    FIELDS.append('start_time')
    FIELDS.append('path_info')
    FIELDS.append('action_and_method')
    FIELDS.append('body')
    FIELDS.append('http_method')
    FIELDS.append('zope_id')
    # fields below are not relevant anymore
    #FIELDS.append('http_host')
    #FIELDS.append('client')
    #FIELDS.append('xff')
    #FIELDS.append('server_name')
    #FIELDS.append('server_port')

    ACTION_REGEX = '"action"\s*:\s*"(.+?)"'
    METHOD_REGEX = '"method"\s*:\s*"(.+?)"'

    DEFAULT_REDIS_URL = 'redis://localhost:6379/0'
    REDIS_KEY_PATTERN = 'ZOPE-REQUEST'
    REDIS_ONGOING_REQUESTS_KEY = 'ZOPE-LOG-ONGOING-REQUESTS'

    REDIS_RECONNECTION_INTERVAL = 60
    ONGOING_REQUEST_LOGGING_CHECK_INTERVAL = 60
    PUSH_TO_REDIS_INTERVAL = 1

    GLOBAL_CONF_VARIABLE = "zope-request-logging"
    OPENTSDB_METRIC_NAME = "zrequest.duration"

    def __init__(self):
        """ """
        self.redis_url = ZopeRequestLogger.get_redis_url()
        self._log_duration = self.get_log_duration() # float indicating min duration to be logged
        self._log_ongoing_requests = False

        self._redis_last_connection_attemp = time.time()
        self._last_ongoing_request_enabled_check = time.time()

        # connect to redis when we need to log a request
        self._redis_client = None

        if self._log_duration > 0:
            log.info("Zope request debug enabled. Logging requests that take longer than: {0} seconds".format(self._log_duration))

    @staticmethod
    def create_redis_client(redis_url):
        client = None
        try:
            client = redis.StrictRedis(**parseRedisUrl(redis_url))
            client.config_get() # test the connection
        except Exception as e:
            client = None
        return client

    @staticmethod
    def get_redis_url():
        config = getGlobalConfiguration()
        return config.get('redis-url', ZopeRequestLogger.DEFAULT_REDIS_URL)

    def get_log_duration(self):
        config = getGlobalConfiguration()
        return float(config.get(self.GLOBAL_CONF_VARIABLE, -1))

    def _extract_action_and_method_from_body(self, body):
        if not body:
            return ""
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

        zope_id = os.environ.get("CONTROLPLANE_INSTANCE_ID", "X")

        data = {}
        user_name = getSecurityManager().getUser().getId()
        data['user_name'] = str(user_name)
        data['start_time'] = str(request._start)
        data['path_info'] = request.get('PATH_INFO', default='')
        data['body'] = request.get('BODY', {})
        data['action_and_method'] = self._extract_action_and_method_from_body(request.get('BODY'))
        data['http_method'] = request.get('method', default='')
        data['zope_id'] = zope_id
        #data['xff'] = request.get('X_FORWARDED_FOR', default='')
        #data['client'] = request.get('REMOTE_ADDR', default='')
        #data['http_host'] = request.get('HTTP_HOST', default='')
        #data['server_name'] = request.get('SERVER_NAME', default='')
        #data['server_port'] = request.get('SERVER_PORT', default='')
        try:
            ident = str(threading.current_thread().ident)
            fingerprint = ":".join((
                ZopeRequestLogger.REDIS_KEY_PATTERN,
                os.environ.get("CONTROLPLANE_SERVICED_ID", "X"),
                str(os.getpid()),
                ident,
                str(zope_id),
                str(int(request._start))
            ))
            request._request_fingerprint = fingerprint
            request._data_to_log = data
        except Exception as ex:
            log.warning("Exception extracting request fingerprint {0}".format(ex))

    def _connected_to_redis(self):
        """ ensures we have a connection to redis """
        if self._redis_client is None:
            now = time.time()
            if now - self._redis_last_connection_attemp > self.REDIS_RECONNECTION_INTERVAL:
                log.info("Trying to reconnect to redis")
                self._redis_last_connection_attemp = now
                self._redis_client = ZopeRequestLogger.create_redis_client(self.redis_url)
                if self._redis_client:
                    log.info("Connected to redis")
                else:
                    log.info("Could not connect to redis")
        return self._redis_client is not None

    def _check_ongoing_requests_enabled(self):
        previous = self._log_ongoing_requests
        if self._redis_client is not None:
            now = time.time()
            if now - self._last_ongoing_request_enabled_check > self.ONGOING_REQUEST_LOGGING_CHECK_INTERVAL:
                self._last_ongoing_request_enabled_check = now
                self._log_ongoing_requests = False
                if self._redis_client.keys(self.REDIS_ONGOING_REQUESTS_KEY):
                    self._log_ongoing_requests = True
        if self._log_ongoing_requests != previous:
            if previous:
                log.info("Zope ongoing requests logging disabled.")
            else:
                log.info("Zope ongoing requests logging enabled.")
        return self._log_ongoing_requests is True

    def _is_relevant_request(self, request):
        """ filter requests we care about for ongoing request logging """
        user = request._data_to_log.get('user_name')
        path = request._data_to_log.get('path_info')
        relevant_user = user and user != str(None)
        relevant_path = path and not path.startswith("/++resource++")
        return relevant_user and relevant_path

    def _get_duration_metric(self, request):
        start = request._start
        duration = time.time() - request._start
        if duration < self._log_duration:
           return {}

        user = request._data_to_log['user_name']
        zope_id = os.environ.get("CONTROLPLANE_INSTANCE_ID", "X")
        path = request._data_to_log['path_info']
        action_and_method = request._data_to_log['action_and_method']

        if not action_and_method: # opentsdb does not like empty strings
            action_and_method = str(None)

        tags = {"zope": zope_id, "user": user, "path": path, "action": action_and_method}

        metric_data = {"timestamp": int(time.time()*1000), "metric": self.OPENTSDB_METRIC_NAME, "value": duration, "tags": tags}

        return metric_data

    def _log_request(self, request, finished=False):
        ''' '''
        # Is redis up?
        if not self._connected_to_redis():
            return

        ongoing_requests_enabled = self._check_ongoing_requests_enabled()

        # Is logging enabled?
        if self._log_duration <=0 and not ongoing_requests_enabled: # logging not enabled
            return

        # store requests info in the request itself
        self._load_data_to_log(request)

        # TODO BATCH REDIS REQUESTS

        # push to redis the opentsdb metric
        if self._log_duration > 0 and finished:
            metric_data = self._get_duration_metric(request)
            if metric_data:
                try:
                    self._redis_client.lpush("metrics", json.dumps(metric_data)) 
                except Exception as e:
                    log.info("Exception trying to push metric to redis: {0}".format(e))
                    self._redis_client = None
                    return

        # log ongoing requests
        if ongoing_requests_enabled and self._is_relevant_request(request):
            redis_key = request._request_fingerprint
            if finished: #delete request from redis
                redis_value = None
            else:
                redis_value = json.dumps(request._data_to_log)

            try:
                if redis_value:
                    self._redis_client.set(redis_key, redis_value)
                    self._redis_client.expire(redis_key, 1*60*60) # Keys expires after 1 hours
                elif self._redis_client.exists(redis_key):
                    self._redis_client.delete(redis_key)
            except Exception as e:
                log.info("Exception trying to push metric to redis: {0}".format(e))
                self._redis_client = None

    def log_request(self, request, finished=False):
        try:
            self._log_request(request, finished)
        except Exception as e:
            # Ensure debugging functinality does not affect the application
            log.debug("Exception logging zope request: {0}".format(e))

