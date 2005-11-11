#################################################################
#
#   Copyright (c) 2003 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""CmdBase

Add data base access functions for command line programs

$Id: ZCmdBase.py,v 1.9 2004/02/16 17:19:31 edahl Exp $"""

__version__ = "$Revision: 1.9 $"[11:-2]

from CmdBase import CmdBase
from Utils import getObjByPath

class DataRootError(Exception):pass

class ZCmdBase(CmdBase):


    def __init__(self, noopts=0, app=None):
        CmdBase.__init__(self, noopts)
        self.dataroot = None
        self.app = app
        self.getDataRoot(app)


    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        CmdBase.buildOptions(self)
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


    def getDataRoot(self, app):
        if not self.dataroot:
            if not self.app: 
                from ZEO import ClientStorage
                from ZODB import DB
                addr = (self.options.host, self.options.port)
                storage=ClientStorage.ClientStorage(addr)
                db=DB(storage)
                connection=db.open()
                root=connection.root()
                self.app=root['Application']
                #import Zope2
                #self.app = Zope2.app()
            self.dataroot = self.app.unrestrictedTraverse(self.options.dataroot)
            self.dmd = self.dataroot


    def getDmdObj(self, path):
        """return an object based on a path starting from the dmd"""
        return self.app.unrestrictedTraverse(self.options.dataroot+path)


    def findDevice(self, name):
        """return a device based on its FQDN"""
        devices = self.dataroot.getDmdRoot("Devices")
        return devices.findDevice(name)
