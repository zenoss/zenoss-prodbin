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
from Products.Five import zcml

from Utils import getObjByPath, zenPath

from Exceptions import ZentinelException
from ZenDaemon import ZenDaemon

from Products.ZenRelations.ZenPropertyManager import setDescriptors

import os
defaultCacheDir = zenPath('var')

class DataRootError(Exception):pass

def login(context, name='admin', userfolder=None):
    '''Logs in.'''
    if userfolder is None:
        userfolder = context.getPhysicalRoot().acl_users
    user = userfolder.getUserById(name)
    if user is None: return
    if not hasattr(user, 'aq_base'):
        user = user.__of__(userfolder)
    newSecurityManager(None, user)
    return user

class ZCmdBase(ZenDaemon):

    def __init__(self, noopts=0, app=None, keeproot=False):
        import Products.ZenossStartup
        zcml.load_site()
        ZenDaemon.__init__(self, noopts, keeproot)
        self.dataroot = None
        self.app = app
        self.db = None
        if not app:
            self.zodbConnect()
        self.poollock = Lock()
        self.getDataRoot()
        self.login()
        setDescriptors(self.dmd.propertyTransformers)

    def zodbConnect(self):
        self.options.port = self.options.port or 3306
        from relstorage.storage import RelStorage
        from relstorage.adapters.mysql import MySQLAdapter
        adapter = MySQLAdapter(
            host=self.options.host,
            port=self.options.port,
            user=self.options.mysqluser,
            passwd=self.options.mysqlpasswd,
            db=self.options.mysqldb
        )
        kwargs = {}
        if self.options.cacheservers:
            kwargs['cache_servers'] = self.options.cacheservers
        if self.options.pollinterval:
            if 'cache_servers' in kwargs:
                if self.options.pollinterval is None:
                    self.log.info("Using default poll-interval of 60 seconds because "
                        "cache-servers was set.")
                    kwargs['poll_interval'] = 60
                else:
                    kwargs['poll_interval'] = self.options.pollinterval
            else:
                self.log.warn("poll-interval of %r is being ignored because "
                    "cache-servers was not set." % self.options.pollinterval)
        self.storage = RelStorage(adapter, **kwargs)
        from ZODB import DB
        self.db = DB(self.storage, cache_size=self.options.cachesize)


    def login(self, name='admin', userfolder=None):
        '''Logs in.'''
        login(self.dmd, name, userfolder)


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
            app = self.getContext(app)
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
        app=root['Application']
        self.app = self.getContext(app)


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

    def sigTerm(self, signum=None, frame=None):
        pass

    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZenDaemon.buildOptions(self)
        self.parser.add_option('-R', '--dataroot',
                    dest="dataroot",
                    default="/zport/dmd",
                    help="root object for data load (i.e. /zport/dmd)")
        self.parser.add_option('--cachesize',
                    dest="cachesize",default=1000, type='int',
                    help="in memory cachesize default: 1000")
        self.parser.add_option('--host',
                    dest="host",default="localhost",
                    help="hostname of MySQL object store")
        self.parser.add_option('--port',
                    dest="port", type="int", default=3306,
                    help="port of MySQL object store")
        self.parser.add_option('--mysqluser', dest='mysqluser', default='zenoss',
                    help='username for MySQL object store')
        self.parser.add_option('--mysqlpasswd', dest='mysqlpasswd', default='zenoss',
                    help='passwd for MySQL object store')
        self.parser.add_option('--mysqldb', dest='mysqldb', default='zodb',
                    help='Name of database for MySQL object store')
        self.parser.add_option('--cacheservers', dest='cacheservers', default="",
                    help='memcached servers to use for object cache (eg. 127.0.0.1:11211)')
        self.parser.add_option('--poll-interval', dest='pollinterval', default=None, type='int',
                    help='Defer polling the database for the specified maximum time interval, in seconds.'
                    ' This will default to 60 only if --cacheservers is set.')

