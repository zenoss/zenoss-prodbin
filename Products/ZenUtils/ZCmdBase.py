#################################################################
#
#   Copyright (c) 2003 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""ZenDaemon

$Id: ZC.py,v 1.9 2004/02/16 17:19:31 edahl Exp $"""

__version__ = "$Revision: 1.9 $"[11:-2]

from ZenDaemon import ZenDaemon
from Utils import getObjByPath

class DataRootError(Exception):pass

class ZCmdBase(ZenDaemon):


    def __init__(self, noopts=0, app=None):
        ZenDaemon.__init__(self, noopts)
        self.dataroot = None
        self.app = app
        self.getDataRoot(app)


    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZenDaemon.buildOptions(self)
        self.parser.add_option('--host',
                    dest="host",default="localhost",
                    help="hostname of zeo server")
        self.parser.add_option('--port',
                    dest="port",type="int", default=8100,
                    help="port of zeo server")
        self.parser.add_option('-R', '--dataroot',
                    dest="dataroot",
                    default="/zport/dmd",
                    help="root object for data load (i.e. /zport/dmd)")

    def opendb(self):
        if self.app: return 
        from ZEO import ClientStorage
        from ZODB import DB
        addr = (self.options.host, self.options.port)
        storage=ClientStorage.ClientStorage(addr)
        db=DB(storage)
        self.connection=db.open()
        root=self.connection.root()
        self.app=root['Application']
        self.getContext()


    def getContext(self):
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
        self.app = self.app.__of__(RequestContainer(REQUEST = req))


    def syncdb(self):
        self.connection.sync()


    def closedb(self):
        self.connection.close()
        self.app = None
        self.dataroot = None
        self.dmd = None


    def getDataRoot(self, app=None):
        if not self.app: self.opendb()
        if not self.dataroot:
            self.dataroot = self.app.unrestrictedTraverse(self.options.dataroot)
            self.dmd = self.dataroot


    def getDmdObj(self, path):
        """return an object based on a path starting from the dmd"""
        return self.app.unrestrictedTraverse(self.options.dataroot+path)


    def findDevice(self, name):
        """return a device based on its FQDN"""
        devices = self.dataroot.getDmdRoot("Devices")
        return devices.findDevice(name)
