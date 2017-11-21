import redis
import logging
import time
import cPickle as pickle

from Products.ZenCallHome.transport import CallHomeData
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.ZenUtils.RedisUtils import parseRedisUrl

log = logging.getLogger('zen.callhomestatus')

class CallHomeStatus(object):
    DEFAULT_REDIS_URL = 'redis://localhost:6379/0'
    REDIS_RECONNECTION_INTERVAL = 3
    STATUS = {'FAILED': -1, 'RUNNING': 0, 'FINISHED': 1, 'PENDING': 2}

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

    def push_to_redis(self, data):
        # Is redis up?
        if not self._connected_to_redis():
            return
        try:
            self._redis_client.set('CallHomeStatus', data)
            log.debug("Success pushed to Redis")
        except Exception as e:
            log.warning("Exception trying to push metric to redis: {0}".format(e))
            self._redis_client = None
            return

    def load_from_redis(self):
        # Is redis up?
        if not self._connected_to_redis():
            return
        data = {}
        try:
            log.debug("Success recived data from Redis")
            return self._redis_client.get('CallHomeStatus')
        except Exception as e:
            log.warning(
                "Exception trying to recive data from redis: {0}".format(e))
            self._redis_client = None
            return

    def stage(self, stage, status="RUNNING", err=""):
        """Usage: obj.stage(Index, Status, Stage error message)
        """
        if stage == "INIT":
            data = {}
            stages = ('Request to CallHome server', 'CallHome start',
                      'Update report', 'CallHome Collect', 'GatherProtocol')
            for v in stages:
                data[v] = {
                    'description': v,
                    'status': '2',
                    'error': '',
                    'stime': '-1'
                }
            data = pickle.dumps(data)
            self.push_to_redis(data)
            return
        data = pickle.loads(self.load_from_redis())
        if status == 0:
            stime = int(time.time())
        else:
            stime = int(time.time()) - int(data[stage]['stime'])
        data[stage] = {
            'description': stage,
            'status': self.STATUS[status],
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
            if val['status'] != 1:
                val['stime'] = -1
            l.append(val)
        return l

