###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2008 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import Globals
from Products.ZenWin.Watcher import Watcher
from Products.ZenWin.WinCollector import WinCollector
from Products.ZenUtils.Driver import drive
from Products.ZenUtils.Timeout import timeout
from Products.ZenEvents.ZenEventClasses import Error, Warning, Info, Debug
from pysamba.library import WError

from twisted.python import failure

class zeneventlog(WinCollector):

    name = agent = "zeneventlog"
    whatIDo = "read the Windows event log"
    eventlogCycleInterval = 5*60
    attributes = WinCollector.attributes + ('eventlogCycleInterval',)
    events = 0


    def fetchDevices(self, driver):
        yield self.configService().callRemote(
            'getDeviceListByMonitor', self.options.monitor)
        yield self.configService().callRemote(
            'getDeviceConfigAndWinServices', driver.next())
        self.updateDevices(driver.next())


    def processDevice(self, device, timeoutSecs):
        """Scan a single device."""
        self.log.debug("polling %s", device.id)
        wql = """SELECT * FROM __InstanceCreationEvent where """\
              """TargetInstance ISA 'Win32_NTLogEvent' """\
              """and TargetInstance.EventType <= %d"""\
              % device.zWinEventlogMinSeverity

        # FIXME: this code looks very similar to the code in zenwin
        def cleanup(result=None):
            if isinstance(result, failure.Failure):
                self.deviceDown(device, result.getErrorMessage())
        def inner(driver):
            try:
                self.niceDoggie(self.cycleInterval())
                w = self.watchers.get(device.id, None)
                if not w:
                    self.log.debug("Creating watcher of %s", device.id)
                    w = Watcher(device, wql)
                    self.log.info("Connecting to %s", device.id)
                    yield w.connect()
                    driver.next()
                    self.log.info("Connected to %s", device.id)
                    self.watchers[device.id] = w

                while 1:
                    queryTimeout = self.wmiqueryTimeout
                    if hasattr( self.options, "queryTimeout") and \
                        self.options.queryTimeout is not None:
                        queryTimeout = int(self.options.queryTimeout)
                    yield w.getEvents(queryTimeout)
                    events = driver.next()
                    self.log.debug("Got %d events", len(events))
                    if not events: break
                    for lrec in events:
                        self.events += 1
                        self.sendEvent(self.makeEvent(device.id, lrec))
                self.deviceUp(device)
            except WError, ex:
                if ex.werror != 0x000006be:
                    raise
                self.log.info("%s: Ignoring event %s "
                              "and restarting connection", device.id, ex)
                cleanup()
            except Exception, ex:
                self.log.exception("Exception getting windows events: %s", ex)
                raise
        d = timeout(drive(inner), timeoutSecs)
        d.addErrback(cleanup)
        return d


    def processLoop(self, devices, timeoutSecs):
        def postStats(result):
            self.sendEvents(
                self.rrdStats.counter('events',
                                      self.cycleInterval(),
                                      self.events))
            return result
        d = WinCollector.processLoop(self, devices, timeoutSecs)
        d.addBoth(postStats)
        return d


    def makeEvent(self, name, lrec):
        """Put event in the queue to be sent to the ZenEventManager.
        """
        lrec = lrec.targetinstance
        evtkey = "%s_%s" % (lrec.sourcename, lrec.eventcode)
        sev = Debug
        if lrec.eventtype == 1:
            sev = Error # error
        elif lrec.eventtype == 2:
            sev = Warning # warning
        elif lrec.eventtype in (3, 4, 5):
            sev = Info # information, security audit success & failure
        evt = dict(device=name,
                   eventClassKey=evtkey,
                   eventGroup=lrec.logfile,
                   component=lrec.sourcename,
                   ntevid=lrec.eventcode,
                   summary=str(lrec.message).strip(),
                   agent="zeneventlog",
                   severity=sev,
                   monitor=self.options.monitor)
        self.log.debug("device:%s msg:'%s'", name, lrec.message)
        return evt


    def cycleInterval(self):
        return self.eventlogCycleInterval
        

if __name__ == "__main__":
    zw = zeneventlog()
    zw.run()
