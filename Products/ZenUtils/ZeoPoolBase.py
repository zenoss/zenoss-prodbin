#################################################################
#
#   Copyright (c) 2003 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""ZeoPoolBase

$Id: ZC.py,v 1.9 2004/02/16 17:19:31 edahl Exp $"""

__version__ = "$Revision: 1.9 $"[11:-2]

from threading import Lock

from ZEO import ClientStorage
from ZODB import DB
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse
from ZPublisher.BaseRequest import RequestContainer

from ZenDaemon import ZenDaemon


class ZeoPoolBase(ZenDaemon):
    """
    A multi-threaded daemon that maintains a pool of zeo connections
    that it can hand out to its worker threads.
    """


    def __init__(self, noopts=0, app=None, keeproot=False):
        ZenDaemon.__init__(self, noopts, keeproot)
        addr = (self.options.host, self.options.port)
        storage=ClientStorage.ClientStorage(addr)
        self.db=DB(storage)
        self.poollock = Lock()


    def getConnection(self):
        """Return a connection from the connection pool.
        """
        try:
            self.poollock.acquire()
            connection=self.db.open()
            root=connection.root()
            app=root['Application']
            self._getContext(app)
            app._p_jar.sync()
            return app
        finally:
            self.poollock.release()


    def closeAll(self):
        """Close all connections in both free an inuse pools.
        """
        self.db.close()


    def _getContext(self, app):
        resp = HTTPResponse(stdout=None)
        env = {
            'SERVER_NAME':'localhost',
            'SERVER_PORT':'8080',
            'REQUEST_METHOD':'GET'
            }
        req = HTTPRequest(None, env, resp)
        app.__of__(RequestContainer(REQUEST = req))
        return app


    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZenDaemon.buildOptions(self)
        self.parser.add_option('--host',
                    dest="host",default="localhost",
                    help="hostname of zeo server")
        self.parser.add_option('--port',
                    dest="port",type="int", default=8100,
                    help="port of zeo server")
