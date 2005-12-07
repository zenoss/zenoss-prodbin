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

import logging

import Globals

from Products.ZenUtils.ZenZopeThread import ZenZopeThread

from Exceptions import ZenEventError

poplog = logging.getLogger("EventPopulator")

class EventPopulator(ZenZopeThread):

    def __init__(self):
        ZenZopeThread.__init__(self)
        self.cycletime = 10
        self.running = False


    def getConfig(self, manager):
        self.cycletime = manager.eventPopCycle
        self.running = manager.eventPopRunning
        self.newevtsel = manager.eventPopSelect
        self.prodfield = manager.ProdStateField
        self.statusTable = manager.statusTable
        self.locfield = manager.lookupManagedEntityField("Location")
        self.dcfield = manager.lookupManagedEntityField("DeviceClass")
        self.sysfield = manager.lookupManagedEntityField("System")
        self.grpfield = manager.lookupManagedEntityField("DeviceGroup")


    def manager(self):
        try:
            return self.app.unrestrictedTraverse("/zport/dmd/ZenEventManager")
        except KeyError:
            raise ZenEventError("unable to open /zport/dmd/ZenEventManager")


    def finddev(self, devname):
        try:
            devs = self.app.unrestrictedTraverse("/zport/dmd/Devices")
            return devs.findDevice(devname)
        except KeyError:
            raise ZenEventError("unable to open /zport/dmd/Devices")


    def getNewEvents(self, db):
        """Get unprocessed events from event backend.
        """
        data = []
        curs = db.cursor()
        curs.execute(self.newevtsel)
        data = curs.fetchall()
        curs.close()
        return data


    def updateEvent(self, db, eventUuid, systems=None, 
                    location=None,productionState=-10,  
                    deviceClass=None, deviceGroups=None):
        """Update event info in unprocessed events.
        """
        update = "update %s set " % self.statusTable
        fields = []
        if systems: fields.append(" %s = '%s'" % (self.sysfield, systems))
        if location: fields.append(" %s = '%s'" % (self.locfield, location))
        if deviceClass: 
            fields.append(" %s = '%s'" % (self.dcfield, deviceClass))
        if deviceGroups: 
            fields.append(" %s = '%s'" % (self.grpfield, deviceGroups))
        fields.append(" %s = %s" % (self.prodfield, productionState))
        update += ",".join(fields)
        update += " where EventUuid = '%s';" % eventUuid
        #print update
        curs = db.cursor()
        curs.execute(update)
        curs.close()


    def processEvents(self, manager):
        """Process new events.
        """
        try:
            db = manager.connect()
            events = self.getNewEvents(db)
            for event in events:
                node, eventUuid = event
                node = manager.cleanstring(node)
                eventUuid = manager.cleanstring(eventUuid)
                dev = self.finddev(node)
                if dev:
                    poplog.debug("device %s found" % node)
                    location = dev.getLocationName()
                    prodstate = dev.productionState
                    devclass  = dev.getDeviceClassName()
                    devgroups = "|"+"|".join(dev.getDeviceGroupNames())
                    devsyss = "|"+"|".join(dev.getSystemNames())
                    self.updateEvent(db, eventUuid, devsyss,
                                    location, prodstate, devclass, devgroups)
                else:
                    self.updateEvent(db, eventUuid)
                    poplog.warn("device %s not found" % node)
            db.close()
        except:
            poplog.exception("problem processing events")

    def loopBody(self):
        try:
            self.opendb()
            manager = self.manager()
            wasrunning = self.running
            self.getConfig(manager)
            if self.running and not wasrunning:
                poplog.info("started")
            if manager.eventPopRunning:
                poplog.debug("starting event processing loop")
                self.processEvents(manager)
                runTime = time.time()-startLoop
                poplog.debug("ending event processing loop")
                poplog.debug("processing loop time = %0.2f seconds",runTime)
            else:
                if not self.running and wasrunning:
                    poplog.warn("stopped")
        finally:
            self.closedb()


    def run(self):
        """Main loop of populator daemon.
        """
        import time
        while 1:
            startLoop = time.time()
            runTime = 0
            try:
                self.loopBody()
            except ZenEventError, e:
                poplog.critical(e)
            except:
                poplog.exception("problem in main loop")
            if runTime < self.cycletime:
                time.sleep(self.cycletime - runTime)
