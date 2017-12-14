import redis
import logging
import time
import cPickle as pickle

from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.ZenUtils.RedisUtils import parseRedisUrl

log = logging.getLogger('zen.callhome')

class CallHomeStatus(object):
    DEFAULT_REDIS_URL = 'redis://localhost:6379/0'
    REDIS_RECONNECTION_INTERVAL = 3
    STATUS = {'FAILED': -1, 'RUNNING': 0, 'FINISHED': 1, 'PENDING': 2}
    REPORT_UPDATE = 'Update report'
    REQUEST_CALLHOME = 'Request to CallHome server'
    START_CALLHOME = 'CallHome start'
    UPDATE_REPORT = 'Update report'
    COLLECT_CALLHOME = 'CallHome Collect'
    GPROTOCOL = 'GatherProtocol'

    def __init__(self):
        self.redis_url = self.get_redis_url()
        self._redis_client = None
        self._redis_last_connection_attemp = 0

    @staticmethod
    def get_redis_url():
        config = getGlobalConfiguration()
        return config.get('redis-url', CallHomeStatus.DEFAULT_REDIS_URL)

    @staticmethod
    def create_redis_client(redis_url):
        client = None
        try:
            client = redis.StrictRedis(**parseRedisUrl(redis_url))
            client.config_get()  # test the connection
        except Exception as e:
            client = None
        return client

    def _connected_to_redis(self):
        """ ensures we have a connection to redis """
        if self._redis_client is None:
            now = time.time()
            if now - self._redis_last_connection_attemp > self.REDIS_RECONNECTION_INTERVAL:
                log.debug("Trying to reconnect to redis")
                self._redis_last_connection_attemp = now
                self._redis_client = self.create_redis_client(self.redis_url)
                if self._redis_client:
                    log.debug("Connected to redis")
                else:
                    log.warning("Could not connect to redis")
        return self._redis_client is not None

    def push_to_redis(self, data, k="CallHomeStatus"):
        # Is redis up?
        if not self._connected_to_redis():
            return
        try:
            self._redis_client.set(k, data)
            log.debug("Success pushed to Redis")
        except Exception as e:
            log.warning("Exception trying to push metric to redis: {0}".format(e))
            self._redis_client = None
            return

    def load_from_redis(self, k="CallHomeStatus"):
        # Is redis up?
        if not self._connected_to_redis():
            return
        try:
            log.debug("Success recived data from Redis")
            return self._redis_client.get(k)
        except Exception as e:
            log.warning(
                "Exception trying to recive data from redis: {0}".format(e))
            self._redis_client = None
            return

    def updateStat(self, param, value):
        data = dict()
        data = pickle.loads(self.load_from_redis())
        data[param] = value
        self.push_to_redis(pickle.dumps(data))

    def getStat(self, param):
        data = dict()
        data = pickle.loads(self.load_from_redis())
        return data.get(param)

    def getStatUI(self):
        """Returns status informations to UI
        """
        l = list()
        data = dict()
        data = pickle.loads(self.load_from_redis())
        l.append({'id': 'lastsuccess', 'description': 'Last success', 'value': data.get('lastSuccess'), 'type': 'date'})
        l.append({'id': 'lastrun', 'description': 'Last run was', 'value': data.get('startedAt'), 'type': 'date'})
        l.append({'id': 'lastupdtook', 'description': 'Last updating took', 'value': data.get('lastTook'), 'type': 'duration'})
        for key, val in data.iteritems():
            if isinstance(val, dict):
                if val.get('status') == "FAILED":
                    err = "Failed: "+val.get('error')
                else:
                    err = "No errors"
        l.append({'id': 'updresult', 'description': 'Updating result', 'value': err, 'type': 'text'})
        return l

    def _init(self):
        """Sets empty data for CallHomeStatus before run
        """
        data = pickle.loads(self.load_from_redis())
        if data is None:
            data = dict()
        stages = ('Request to CallHome server', 'CallHome start',
                  'Update report', 'CallHome Collect', 'GatherProtocol')
        for v in stages:
            data[v] = {
                'description': v,
                'status': 'PENDING',
                'error': '',
                'stime': '-1'
            }
        log.debug("Setted empty data for CallHomeStatus")
        data = pickle.dumps(data)
        self.push_to_redis(data)

    def stage(self, stage, status="RUNNING", err=""):
        """Usage: obj.stage(Stage name, Stage Status, Stage error message)
        """
        if stage == "Update report" and status == "RUNNING":
            self._init()
            self.updateStat('startedAt', int(time.time()))
        data = dict()
        data = pickle.loads(self.load_from_redis())
        if stage == "Update report" and status == "FINISHED":
            self.updateStat('lastTook', int(time.time()) - int(data[stage]['stime']))
        #data = dict()
        #data = pickle.loads(self.load_from_redis())
        if status == "RUNNING":
            stime = int(time.time())
        else:
            stime = int(time.time()) - int(data[stage]['stime'])
        data[stage] = {
            'description': stage,
            'status': status,
            'error': err,
            'stime': stime
        }
        self.push_to_redis(pickle.dumps(data))

    def status(self):
        l = list()
        d = dict()
        try:
            d = pickle.loads(self.load_from_redis())
        except Exception as e:
            log.warning("Failed to load pickle loads: {0}".format(e))
        for key, val in d.iteritems():
            if isinstance(val, dict):
                if val['status'] != "FINISHED":
                    val['stime'] = -1
                l.append(val)
        return l

