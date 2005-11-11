#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""EventPopulator

Populate netcool events based on the data model.
Calls to getDeviceEventInfo on Confmon.DeviceClass
to get the data list to populate into the events.  Requires
Sybase libraries to interact with Omnibus database.

$Id: EventPopulator.py,v 1.21 2003/05/16 21:00:32 edahl Exp $"""

__version__ = "$Revision: 1.21 $"[11:-2]

import socket
import time
import sys
import os.path
import logging
import xmlrpclib

import Globals

from Products.ZenUtils.ZenZopeThread import ZenZopeThread

from DbAccessBase import DbAccessBase

class EventPopulator(ZenZopeThread):

    def __init__(self):
        ZenZopeThread.__init__(self)
        self.cycletime = 10
        self.opendb()
        manager = self.manager()
        self.cycletime = manager.eventPopCycle
        self.newevtsel = manager.eventPopSelect
        self.prodfield = manager.ProdStateField
        self.locfield = manager.lookupManagedEntityField("Location")
        self.dcfield = manager.lookupManagedEntityField("DeviceClass")
        self.sysfield = manager.lookupManagedEntityField("System")
        self.grpfield = manager.lookupManagedEntityField("DeviceGroup")
        self.closedb()


    def manager(self)
        return self.app.zport.dmd.ZenEventManager


    def finddev(self, devname):
        return self.app.zport.dmd.Devices.findDevice(devname)


    def getNewEvents(self, db):
        """Get unprocessed events from event backend.
        """
        data = []
        curs = db.cursor()
        curs.execute(newevtsel)
        data = curs.fetchall()
        return data


    def updateEvent(self, curs, serverSerial, serverName, 
                    systems=None, location=None,productionState=-10,  
                    deviceClass=None, deviceGroups=None):
        """Update event info in unprocessed events.
        """
        update = "update status set "
        if systems: update += " %s = '%s'" % (self.sysfield, systemName) 
        if location: update += " %s = '%s'" % (self.locfield, location)
        if deviceClass: update += " %s = '%s'" % (self.dcfield, deviceClass)
        if deviceGroups: update += " %s = '%s'" % (self.grpfield, deviceGroups)
        update += " %s = %s" % (self.prodfield, productionState) 
        update += " where ServerSerial = '%s' and ServerName = '%s';" % (
                        serverSerial serverName)
        #print update
        curs.execute(update)


    def processEvents(self):
        """Process new events.
        """
        try:
            self.opendb()
            db = self.manager().connect()
            events = self.getNewEvents(db)
            curs = db.cursor()
            for event in events:
                node, serverSerial, serverName = event
                node = self.cleanstring(node)
                serverName = self.cleanstring(serverName)
                dev = self.finddev(node):
                if dev:
                    self.log.info("device %s found" % node)
                    location = dev.getLocationName()
                    prodstate = dev.productionState
                    devclass  = dev.getDeviceClassName()
                    devgroups = dev.getDeviceGroupNames()
                    devsyss = dev.getSystemNames()
                    self.updateEvent(curs, serverSerial, serverName, devsyss,
                                    location, prodstate, devclass, devgroups)
                else:
                    self.updateEvent(curs, serverSerial, serverName)
                    self.log.warn("device %s not found" % node)
            db.close()
            self.closedb()
        except:
            self.log.exception("Problem processing events")


    def run(self):
        """Main loop of populator daemon.
        """
        while 1:
            startLoop = time.time()
            logging.info("Starting event processing loop")
            self.getDeviceInfo()
            self.processEvents()
            runTime = time.time()-startLoop
            logging.info("Ending event processing loop")
            logging.info("Loop runtime = %s seconds" % runTime)
            if runTime < self.cycletime:
                time.sleep(self.cycletime - runTime)
