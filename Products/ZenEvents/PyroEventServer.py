###############################################################################
#
#   Copyright (c) 2004 Zentinel Systems. 
#
#   This library is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public
#   License as published by the Free Software Foundation; either
#   version 2.1 of the License, or (at your option) any later version.
#
###############################################################################

import os
from threading import Timer

import Pyro.core

from Products.ZenEvents.EventDatabase import EventDatabase
from Products.ZenEvents.EventDatabase import defaultPickleName, defaultSaveTime

class PyroEventDatabase(Pyro.core.ObjBase, EventDatabase):
    def __init__(self, savefile=defaultPickleName, 
                       savetime=defaultSaveTime,
                       journal=True):
        Pyro.core.ObjBase.__init__(self)
        EventDatabase.__init__(self, savefile, savetime, journal) 


class PyroEventServer(Pyro.core.ObjBase):
    
    def __init__(self, databaseDir=os.getcwd()):
        Pyro.core.ObjBase.__init__(self)
        self.databaseDir = databaseDir
        self.databases = {}
    
    def createDatabase(self, databaseName, **kargs):
        """add a new database to the event server it will get autoloaded
        when the server is started"""
        pass

    def openDatabase(self, databaseName, **kargs):
        """open an event database for usage"""
        print self.getLocalStorage().caller
        if self.databases.has_key(databaseName):
            return self.databases[databaseName].uri 
        savefile = os.path.join(self.databaseDir, databaseName)
        kargs['savefile'] = savefile
        self.databases[databaseName] = PyroEventDatabase(savefile=savefile)
        uri = daemon.connect(self.databases[databaseName], databaseName)
        self.databases[databaseName].uri = uri
        return uri
        
    def closeDatabase(self, databaseName):
        """checkpoint the database and remove it from the request broker"""
        db = self.databases[databaseName]
        daemon.disconnect(db)
        db.close()
        del self.databases[databaseName]

    def _closeDatabases(self):
        """close all open databases"""
        for db in self.databases.values():
            daemon.disconnect(db)
            db.close()
    
    def __del__(self):
        Pyro.core.ObjBase.__del__(self) 
        self._closeDatabases()


Pyro.core.initServer()
daemon=Pyro.core.Daemon()
uri=daemon.connect(PyroEventServer(),"EventServer")
print "The daemon runs on port:",daemon.port
print "The object's uri is:",uri
daemon.requestLoop()
