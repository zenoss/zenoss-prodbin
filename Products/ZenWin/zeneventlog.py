#! /usr/bin/env python
# -*- coding: utf-8 -*-
# ##########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
# ##########################################################################

__doc__ = """zeneventlog
    Connect using WMI to gather the Windows Event Log and create
    Zenoss events.
"""

import Globals
from Products.ZenWin.Watcher import Watcher
from Products.ZenWin.WinCollector import WinCollector
from Products.ZenUtils.Driver import drive
from Products.ZenUtils.Timeout import timeout
from Products.ZenEvents.ZenEventClasses import Error, Warning, Info, \
    Debug
from pysamba.library import WError

from twisted.python import failure


class zeneventlog(WinCollector):
    """
    Connect using WMI to gather the Windows Event Log and create
    Zenoss events.
    """
    name = agent = 'zeneventlog'
    whatIDo = 'read the Windows event log'
    eventlogCycleInterval = 5 * 60
    attributes = WinCollector.attributes + ('eventlogCycleInterval', )
    events = 0

    def fetchDevices(self, driver):
        """
        Generator function to return the list of devices to gather
        Event log information.   
        
        @param driver: driver
        @type driver: driver object
        @return: objects
        @rtype: object
        """
        yield self.configService().callRemote('getDeviceListByMonitor',
                self.options.monitor)
        yield self.configService().callRemote('getDeviceConfigAndWinServices',
                driver.next())
        self.updateDevices(driver.next())

    def processDevice(self, device, timeoutSecs):
        """
        Scan a single device.
        
        @param device: device to interrogate
        @type device: device object
        @param timeoutSecs: timeoutSecs
        @type timeoutSecs: int
        @return: objects
        @rtype: objects
        """
        self.log.debug('Polling %s' % device.id)
        wql = "SELECT * FROM __InstanceCreationEvent where TargetInstance ISA 'Win32_NTLogEvent' and TargetInstance.EventType <= %d"\
             % device.zWinEventlogMinSeverity

# FIXME: this code looks very similar to the code in zenwin
        def cleanup(result=None):
            """
            Set a device to be down on failure conditions
            """
            if isinstance(result, failure.Failure):
                self.deviceDown(device, result.getErrorMessage())

        def inner(driver):
            """
            inner
            
            @param driver: driver
            @type driver: string
            @return: objects
            @rtype: objects
            """
            try:
                self.niceDoggie(self.cycleInterval())
                w = self.watchers.get(device.id, None)
                if not w:
                    self.log.debug('Creating watcher of %s', device.id)
                    w = Watcher(device, wql)
                    self.log.info('Connecting to %s', device.id)
                    yield w.connect()
                    driver.next()
                    self.log.info('Connected to %s', device.id)
                    self.watchers[device.id] = w

                while 1:
                    queryTimeout = self.wmiqueryTimeout
                    if hasattr( self.options, "queryTimeout") and \
                        self.options.queryTimeout is not None:
                        queryTimeout = int(self.options.queryTimeout)
                    yield w.getEvents(queryTimeout)
                    events = driver.next()
                    self.log.debug('Got %d events', len(events))
                    if not events:
                        break
                    for lrec in events:
                        self.events += 1
                        self.sendEvent(self.makeEvent(device.id, lrec))
                self.deviceUp(device)

            except WError, ex:
                if ex.werror != 0x000006be:
                    # OPERATION_COULD_NOT_BE_COMPLETED
                    raise
                self.log.info('%s: Ignoring event %s and restarting connection',
                              device.id, ex)
                cleanup()
            except Exception, ex:
                self.log.exception('Exception getting windows events: %s', ex)
                raise

        d = timeout(drive(inner), timeoutSecs)
        d.addErrback(cleanup)
        return d

    def processLoop(self, devices, timeoutSecs):
        """
        Kick off the main loop of collecting data
        
        @param devices: devices
        @type devices: string
        @param timeoutSecs: timeoutSecs
        @type timeoutSecs: string
        @return: defered
        @rtype: Twisted defered
        """
        def postStats(result):
            """
            Twisted callback to report evnets
            
            @param result: result of operation
            @type result: string
            @return: result
            @rtype: string
            """
            self.sendEvents(self.rrdStats.counter('events',
                            self.cycleInterval(), self.events))
            return result

        d = WinCollector.processLoop(self, devices, timeoutSecs)
        d.addBoth(postStats)
        return d

    def makeEvent(self, name, lrec):
        """
        Put event in the queue to be sent to the ZenEventManager.
        
        @param name: name of the device
        @type name: string
        @param lrec: log record
        @type lrec: log record object
        @return: dictionary with event keys and values
        @rtype: dictionary
        """
        lrec = lrec.targetinstance
        evtkey = '%s_%s' % (lrec.sourcename, lrec.eventcode)
        sev = Debug
        if lrec.eventtype == 1:
            sev = Error  # error
        elif lrec.eventtype == 2:
            sev = Warning  # warning
        elif lrec.eventtype in (3, 4, 5):
            sev = Info  # information, security audit success & failure

        evt = dict(
            device=name,
            eventClassKey=evtkey,
            eventGroup=lrec.logfile,
            component=lrec.sourcename,
            ntevid=lrec.eventcode,
            summary=str(lrec.message).strip(),
            agent='zeneventlog',
            severity=sev,
            monitor=self.options.monitor,
            )
        self.log.debug("Device:%s msg:'%s'", name, lrec.message)
        return evt

    def cycleInterval(self):
        """
        Return the length of the cycleInterval
        
        @return: number of seconds to repeat a collection cycle
        @rtype: int
        """
        return self.eventlogCycleInterval


if __name__ == '__main__':
    zw = zeneventlog()
    zw.run()
