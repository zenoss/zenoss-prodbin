###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import MySQLdb
import MySQLdb.converters
from MySQLdb.constants import FIELD_TYPE

import time
import DateTime

from Queue import Queue, Empty, Full

import logging
log = logging.getLogger("zen.DbConnectionPool")

POOL_SIZE = 5
KEEP_ALIVE = 28800

class DbConnectionPool:

    def __new__(self):                  # self is a type
        if not '_the_instance' in self.__dict__:
            self._the_instance = object.__new__(self)
        return self._the_instance
        
    '''
    instance = None
    def __new__(cls, *args, **kargs): 
        if cls.instance is None:
            cls.instance = object.__new__(cls, *args, **kargs)
        log.debug('Returning single instance of DbConnectionPool')
        return cls.instance
    '''
        
    def __init__(self):
        self.q = Queue(POOL_SIZE)

    def qsize(self):
        return self.q.qsize()

    def get(self, host=None, port=None, username=None, 
            password=None, database=None, block=0):
        try:
            putstamp,obj = self.q.get(block)

            if time.time() - putstamp >= KEEP_ALIVE:
                log.debug('Retrieved a stale connection; Pool size: %s' % self.qsize())
                obj.close()
                return self._createConnection(host=host, port=port, 
                                            username=username, 
                                            password=password,
                                            database=database)
            else:
                log.debug('Retrieved a connection; Pool size: %s' % self.qsize())
                if hasattr(obj, 'ping'):
                    # maybe the connection timed out: reconnect if necessary
                    obj.ping()
                return obj

        except Empty:
            return self._createConnection(host=host, port=port, 
                                        username=username, 
                                        password=password,
                                        database=database)

    def put(self, obj, block=0):
        try:
            self.q.put((time.time(),obj), block)
            log.debug('Returned a connection; Pool size: %s' % self.qsize())
        except Full:
            pass

    def _createConnection(self, host=None, port=None, 
                        username=None, password=None, database=None):
        log.debug('Creating a new connection; Pool size: %s' % self.qsize())
        conn = None
        mysqlconv = MySQLdb.converters.conversions.copy()
        mysqlconv[FIELD_TYPE.DATETIME] = DateTime.DateTime
        mysqlconv[FIELD_TYPE.TIMESTAMP] = DateTime.DateTime
        # FIXME for some reason it thinks my int is a long -EAD
        mysqlconv[FIELD_TYPE.LONG] = int
        if not host:
            host, database = database, 'events'
        if port:
            port = int(port)
        conn = MySQLdb.connect(host=host, user=username,
                               port=port, passwd=password, 
                               db=database, conv=mysqlconv, reconnect=1)
        conn.autocommit(1)
        return conn
