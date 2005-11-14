#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""MaintenanceThread

$Id: MaintenanceThread.py,v 1.21 2003/05/16 21:00:32 edahl Exp $"""

__version__ = "$Revision: 1.21 $"[11:-2]

import logging

import Globals

from Products.ZenUtils.ZenZopeThread import ZenZopeThread

from Exceptions import ZenEventError

mlog = logging.getLogger("MaintenanceThread")

class MaintenanceThread(ZenZopeThread):

    def __init__(self):
        ZenZopeThread.__init__(self)
        self.cycletime = 10
        self.running = False


    def getConfig(self, manager):
        self.cycletime = manager.maintenanceCycle
        self.running = manager.maintenanceRunning
        self.procs = manager.maintenanceProcedures


    def manager(self):
        try:
            return self.app.unrestrictedTraverse("/zport/dmd/ZenEventManager")
        except KeyError:
            raise ZenEventError("unable to open /zport/dmd/ZenEventManager")


    def close_events(self, db):
        select = "select Node, Component, Class, AlertKey FROM status WHERE Severity = 0;"
        delete = "delete from status where Node=%s and Component=%s and Class=%s and AlertKey=%s;"
        curs = db.cursor()
        curs.execute(select)
        for row in curs.fetchall():
            curs.execute(delete, row)
        curs.close()    
   

    def processProcs(self, manager):
        """Process new events.
        """
        try:
            db = manager.connect()
            #self.close_events(db)
            curs = db.cursor()
            for proc in self.procs:
                try:
                    curs.execute("call %s();" % proc)
                except:
                    mlog.exception("problem running proc: '%s'", proc)
            db.close()
        except:
            mlog.exception("problem processing procedures")


    def run(self):
        """Main loop of populator daemon.
        """
        import time
        while 1:
            startLoop = time.time()
            runTime = 0
            try:
                self.opendb()
                manager = self.manager()
                wasrunning = self.running
                self.getConfig(manager)
                if self.running and not wasrunning:
                    mlog.info("started")
                if manager.maintenanceRunning:
                    mlog.debug("starting maintenance loop")
                    self.processProcs(manager)
                    runTime = time.time()-startLoop
                    mlog.debug("ending maintenance loop")
                    mlog.debug("maintenance loop time = %0.2f seconds",runTime)
                else:
                    if not self.running and wasrunning:
                        mlog.warn("stopped")
            except ZenEventError, e:
                mlog.critical(e)
            except:
                mlog.exception("problem in main loop")
            self.closedb()
            if runTime < self.cycletime:
                time.sleep(self.cycletime - runTime)

