import MySQLdb
import MySQLdb.converters
from MySQLdb.constants import FIELD_TYPE

import time
import DateTime

from Queue import Queue, Empty, Full

POOL_SIZE = 5
KEEP_ALIVE = 28800

class DbConnectionPool(Queue):

    instance = None
    def __new__(cls, *args, **kargs): 
        if cls.instance is None:
            cls.instance = object.__new__(cls, *args, **kargs)
        return cls.instance
        
    def __init__(self):
        Queue.__init__(self, POOL_SIZE)

    def get(self, backend=None, host=None, port=None, username=None, 
            password=None, database=None, block=0):
        try:
            putstamp,obj = Queue.get(self, block)

            if time.time() - putstamp >= KEEP_ALIVE: 
                obj.close()
                return self._createConnection(host=host, port=port, 
                                            username=username, 
                                            password=password,
                                            database=database)
            else:    
                return obj

        except Empty:
            return self._createConnection(host=host, port=port, 
                                        username=username, 
                                        password=password,
                                        database=database)

    def put(self, obj, block=0):
        try:
            Queue.put(self, (time.time(),obj), block)
        except Full:
            pass

    def _createConnection(self, host=None, port=None, 
                        username=None, password=None, database=None):
        conn = None
        """
        if self.backend == "omnibus":
            import Sybase
            self.conn = Sybase.connect(self.database,self.username,
                                        self.password)
        elif self.backend == "oracle":
            import DCOracle2
            connstr = "%s/%s@%s" % (self.username, self.password, self.database)
            self.conn = DCOracle2.connect(connstr)                                        
        elif self.backend == "mysql":
        """
        mysqlconv = MySQLdb.converters.conversions.copy()
        mysqlconv[FIELD_TYPE.DATETIME] = DateTime.DateTime
        mysqlconv[FIELD_TYPE.TIMESTAMP] = DateTime.DateTime
        # FIXME for some reason it thinks my int is a long -EAD
        mysqlconv[FIELD_TYPE.LONG] = int
        if not host:
            host, database = database, 'events'
        conn = MySQLdb.connect(host=host, user=username,
                             port=port, passwd=password, 
                             db=database, conv=mysqlconv)
        conn.autocommit(1)
        return conn