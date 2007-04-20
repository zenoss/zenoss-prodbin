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


class ZeoConn(object):

    def __init__(self, host="localhost", port=8100):
        from ZEO import ClientStorage
        from ZODB import DB
        addr = (host, port)
        storage=ClientStorage.ClientStorage(addr)
        self.db=DB(storage)
        self.app = None
        self.dmd = None
        self.opendb()


    def opendb(self):
        if self.app: return 
        self.connection=self.db.open()
        root=self.connection.root()
        self.app=root['Application']
        self._getContext(self.app)
        self.dmd = self.app.zport.dmd


    def syncdb(self):
        self.connection.sync()


    def closedb(self):
        self.connection.close()
        self.db.close()
        self.app = None
        self.dmd = None
    
    
    def _getContext(self, app):
        from ZPublisher.HTTPRequest import HTTPRequest
        from ZPublisher.HTTPResponse import HTTPResponse
        from ZPublisher.BaseRequest import RequestContainer
        resp = HTTPResponse(stdout=None)
        env = {
            'SERVER_NAME':'localhost',
            'SERVER_PORT':'8080',
            'REQUEST_METHOD':'GET'
            }
        req = HTTPRequest(None, env, resp)
        return app.__of__(RequestContainer(REQUEST = req))


