#! /usr/bin/env python 
#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''Schedule

Walk through the maintenance schedule.

$Id$
'''
import time
import logging
import transaction
from twisted.internet import reactor

class Schedule:

    def __init__(self, options, dmd):
        "start executing the schedule"
        self.dmd = dmd
        self.maintenance = []
        self.options = options
        self.log = logging.getLogger("zen.Schedule")
        self.workList = []
        self.timer = None


    def buildOptions(self, parser):
        "Set options in a borrowed parser"


    def start(self):
        "Start working the schedule"
        self.configCycle()


    def configCycle(self):
        "Basic event-driven config loop"
        self.run()
        reactor.callLater(self.options.cycletime, self.configCycle)


    def sync(self):
        "Synch with the database"
        self.dmd._p_jar.sync()    

    def getWindows(self):
        result = []
        for dev in self.dmd.Devices.getSubDevices():
            result.extend(dev.maintenanceWindows())
        for name in 'Systems', 'Locations', 'Groups', 'Devices':
            organizer = getattr(self.dmd, name)
            for c in organizer.getSubOrganizers():
                result.extend(c.maintenanceWindows())
            result.extend(organizer.maintenanceWindows())
            
        for us in self.dmd.ZenUsers.getAllUserSettings():
            for ar in us.objectValues(spec="ActionRule"):
                result.extend([w for w in ar.windows() if w.enabled])
        return result
        
    def run(self):
        "Re-read work list from the database"
        self.sync()
        self.workList = self.getWindows()
        self.runEvents()

    def makeWorkList(self, now, workList):
        work = [(mw.nextEvent(now), mw) for mw in workList]
        work.sort()
        # note that None is less than any number of seconds
        while len(work):
            t, mw = work[0]
            if t: break
            if mw.enabled:
                self.log.debug("Never going to run Maintenance "
                               "Window %s for %s again",
                               mw.getId(), mw.target().getId())
            if mw.started:
                mw.end()
            work.pop(0)
        return work

    def now(self):
        return time.time()

    def runEvents(self):
        "Execute all the maintanance windows at the proper time"

        if self.timer and not self.timer.called:
            self.timer.cancel()

        # sort events by the next occurance of something to do
        now = self.now()
        work = self.makeWorkList(now, self.workList)
        self.workList = [mw for t, mw in work]

        # fire events that should be done now
        for next, mw in work:
            if next <= now:
                how = {True:'stopping', False:'starting'}[bool(mw.started)]
                self.log.debug("Maintenance window "
                               "%s %s for %s",
                               how, mw.getId(), mw.target().getId())
                self.executeMaintenanceWindow(mw, next)
            else:
                break

        work = self.makeWorkList(now, self.workList)
        if work:
            wait = work[0][0] - now
            self.log.debug("Waiting %f seconds", wait)
            self.timer = self.callLater(wait)
        self.commit()

    def commit(self):
        transaction.commit()

    def callLater(self, seconds):
        return reactor.callLater(seconds, self.runEvents)

    def executeMaintenanceWindow(self, mw, timestamp):
        mw.execute(timestamp)

if __name__ == "__main__":
    class MySchedule(Schedule):
        currentTime = time.time()
        objs = None
        def now(self):
            return self.currentTime
        def callLater(self, seconds):
            self.currentTime += seconds
        def executeMaintenanceWindow(self, mw, timestamp):
            print 'executing', mw.id, time.ctime(timestamp)
            mw.execute(timestamp)
        def getWindows(self):
            if self.workList:
                return self.workList
            return Schedule.getWindows(self)
        def commit(self):
            pass
        sync = commit

    import Globals
    from Products.ZenUtils.ZCmdBase import ZCmdBase

    cmd = ZCmdBase()
    class Options: pass
    s = MySchedule(Options(), cmd.dmd)
    # compute the schedule for 30 days
    end = s.currentTime + 60*60*24*30
    while s.currentTime < end:
        s.run()
