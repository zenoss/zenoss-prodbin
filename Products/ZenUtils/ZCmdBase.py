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

__doc__="""ZenDaemon

$Id: ZC.py,v 1.9 2004/02/16 17:19:31 edahl Exp $"""

__version__ = "$Revision: 1.9 $"[11:-2]

from threading import Lock

from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager
from Utils import getObjByPath

from Exceptions import ZentinelException
from ZenDaemon import ZenDaemon

import os
defaultCacheDir = os.getenv('ZENHOME')
if defaultCacheDir is not None:
    defaultCacheDir = os.path.join(defaultCacheDir, 'var')

class DataRootError(Exception):pass

class ZCmdBase(ZenDaemon):


    def __init__(self, noopts=0, app=None, keeproot=False):
        ZenDaemon.__init__(self, noopts, keeproot)
        self.dataroot = None
        self.app = app
        self.db = None
        if not app:
            try:
                self.zeoConnect()
            except ValueError:
                cache = os.path.join(self.options.pcachedir,
                                     '%s.zec' % self.options.pcachename)
                if os.path.exists(cache):
                    self.log.warning("Deleting corrupted cache %s" % cache)
                    os.unlink(cache)
                    self.zeoConnect()
                else: 
                    raise
        self.poollock = Lock()
        self.getDataRoot()
        self.login()

    def zeoConnect(self):
        from ZEO.ClientStorage import ClientStorage
        storage=ClientStorage((self.options.host, self.options.port),
                              client=self.options.pcachename,
                              var=self.options.pcachedir,
                              cache_size=self.options.pcachesize*1024*1024)
        from ZODB import DB
        self.db = DB(storage, cache_size=self.options.cachesize)


    def login(self, name='admin', userfolder=None):
        '''Logs in.'''
        if userfolder is None:
            userfolder = self.app.acl_users
        user = userfolder.getUserById(name)
        if user is None: return
        if not hasattr(user, 'aq_base'):
            user = user.__of__(userfolder)
        newSecurityManager(None, user)


    def logout(self):
        '''Logs out.'''
        noSecurityManager()


    def getConnection(self):
        """Return a wrapped app connection from the connection pool.
        """
        if not self.db:
            raise ZentinelException(
                "running inside zope can't open connections.")
        try:
            self.poollock.acquire()
            connection=self.db.open()
            root=connection.root()
            app=root['Application']
            self.getContext(app)
            app._p_jar.sync()
            return app
        finally:
            self.poollock.release()


    def closeAll(self):
        """Close all connections in both free an inuse pools.
        """
        self.db.close()


    def opendb(self):
        if self.app: return 
        self.connection=self.db.open()
        root=self.connection.root()
        self.app=root['Application']
        self.getContext(self.app)


    def syncdb(self):
        self.connection.sync()


    def closedb(self):
        self.connection.close()
        #self.db.close()
        self.app = None
        self.dataroot = None
        self.dmd = None


    def getDataRoot(self):
        if not self.app: self.opendb()
        if not self.dataroot:
            self.dataroot = getObjByPath(self.app, self.options.dataroot)
            self.dmd = self.dataroot


    def getContext(self, app):
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


    def getDmdObj(self, path):
        """return an object based on a path starting from the dmd"""
        return getObjByPath(self.app, self.options.dataroot+path)


    def findDevice(self, name):
        """return a device based on its FQDN"""
        devices = self.dataroot.getDmdRoot("Devices")
        return devices.findDevice(name)
    
    
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
        self.parser.add_option('--cachesize',
                    dest="cachesize",default=1000, type='int',
                    help="in memory cachesize default: 1000")
        self.parser.add_option('--pcachename',
                    dest="pcachename",default=None,
                    help="persistent cache file name default:None")
        self.parser.add_option('--pcachedir',
                    dest="pcachedir",default=defaultCacheDir,
                    help="persistent cache file directory")
        self.parser.add_option('--pcachesize',
                    dest="pcachesize",default=10, type='int',
                    help="persistent cache file size in MB")
