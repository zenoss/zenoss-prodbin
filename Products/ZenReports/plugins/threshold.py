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
__doc__="The threshold report."

import time
import Globals
from Products.ZenUtils.Time import Duration
from Products.ZenReports import Utils

def dateAsFloat(args, key, default):
    from Products.ZenUtils.Time import ParseUSDate
    if args.has_key(key):
        args[key] = ParseUSDate(args[key])
    else:
        args[key] = default

class threshold:

    def run(self, dmd, args):
        zem = dmd.ZenEventManager
        start = time.time() - zem.defaultAvailabilityDays*24*60*60
        dateAsFloat(args, 'startDate', start)
        dateAsFloat(args, 'endDate', time.time())
        args['eventClass'] = args.get('eventClass', '') or '/Perf'

        # Get all the threshold related events from summary and history
        report = []
        w =  ' WHERE severity >= 3 '
        w += ' AND lastTime > %(startDate)s '
        w += ' AND firstTime <= %(endDate)s '
        w += ' AND firstTime != lastTime '
        w += ' AND (eventClass = "%(eventClass)s" '
        w +=  ' or eventClass like "%(eventClass)s/%%") '

        args['cols'] = 'device, component, eventClass,  firstTime, lastTime '
        w %= args
        args['w'] = w
        query = ('SELECT %(cols)s FROM ( '
                 ' SELECT %(cols)s FROM history %(w)s '
                 '  UNION '
                 ' SELECT %(cols)s FROM status %(w)s '
                 ') AS U ' % args)

        sum = {}
        counts = {}
        zem = dmd.ZenEventManager
        conn = zem.connect()
        try:
            curs = conn.cursor()
            curs.execute(query)
            startDate = args['startDate']
            endDate = args['endDate']
            while 1:
                rows = curs.fetchmany()
                if not rows: break
                for row in rows:
                    device, component, eventClass, firstTime, lastTime = row
                    firstTime = max(firstTime, startDate)
                    lastTime = min(lastTime, endDate)
                    diff = lastTime - firstTime
                    if diff > 0.0:
                        try:
                            sum[(device, component, eventClass)] += diff
                            counts[(device, component, eventClass)] += 1
                        except KeyError:
                            sum[(device, component, eventClass)] = diff
                            counts[(device, component, eventClass)] = 1
        finally: zem.close(conn)

        # Look up objects that correspond to the names
        find = dmd.Devices.findDevice
        totalTime = endDate - startDate
        for k, seconds in sum.items():
            deviceName, componentName, eventClassName = k
            deviceLink = deviceName
            component = None
            componentLink = componentName
            eventClass = None
            eventClassLink = eventClassName
            device = find(deviceName)
            if not device or not dmd.checkRemotePerm('View', device): continue
            deviceLink = device.urlLink()
            if componentName:
                for c in device.getMonitoredComponents():
                    if c.name().find(componentName) >= 0:
                        component = c
                        componentLink = c.urlLink()
                        break
            # get some values useful for the report
            duration = Duration(seconds)
            percent = seconds * 100. / totalTime
            try:
                eventClass = dmd.Events.getOrganizer(eventClassName)
                eventClassLink = eventClass.urlLink()
            except KeyError:
                pass
            report.append(Utils.Record(
                deviceName=deviceName,
                deviceLink=deviceLink,
                componentName=componentName,
                componentLink=componentLink,
                eventClassName=eventClassName,
                eventClassLink=eventClassLink,
                count=counts.get(k, 1),
                seconds=seconds,
                percentTime=percent,
                duration=duration))

        return report

