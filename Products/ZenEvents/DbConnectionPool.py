import MySQLdb

import time

from Queue import Queue, Empty, Full

from DbAccessBase import DbAccessBase

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

    def get(self, backend, host, port, username, password, database, block=0):

        try:
            putstamp,obj = Queue.get(self, block)

            # don't return stale connection, this needs to match whatever your 
            # connection keep alive value is in MySQL            

            if time.time() - putstamp >= KEEP_ALIVE: 
                obj.close()
                return DbAccessBase(backend=backend, 
                                    host=host, 
                                    port=port, 
                                    username=username, 
                                    password=password, 
                                    database=database)        
            else:    
                return obj

        except Empty:
            return DbAccessBase(backend=backend, 
                                host=host, 
                                port=port, 
                                username=username, 
                                password=password, 
                                database=database)

    def put(self, obj, block=0):

        try:
            Queue.put(self, (time.time(),obj), block)
        except Full:
            pass

