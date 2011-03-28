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
from collections import defaultdict
from itertools import chain
import Globals
from Products.ZenUtils.Time import Duration, getBeginningOfDay, getEndOfDay
from Products.ZenReports import Utils
from Products.Zuul import getFacade
from Products.ZenEvents.Availability import Availability, _severityGreaterThanOrEqual, CLOSED_EVENT_STATUSES
from zenoss.protocols.protobufs.zep_pb2 import (SEVERITY_CRITICAL, SEVERITY_ERROR,
                                                SEVERITY_WARNING, SEVERITY_INFO,
                                                SEVERITY_DEBUG, SEVERITY_CLEAR)


def dateAsFloat(args, key, default):
    from Products.ZenUtils.Time import ParseUSDate
    if key in args:
        args[key] = ParseUSDate(args[key])
    else:
        args[key] = default

class threshold(object):

    def run(self, dmd, args):
        now = time.time()
        zep = getFacade("zep", dmd)

        # read in args
        dateAsFloat(args, 'startDate', Availability.getDefaultAvailabilityStart())
        dateAsFloat(args, 'endDate', Availability.getDefaultAvailabilityEnd())
        args['eventClass'] = args.get('eventClass', '') or '/Perf'

        startDate = min(args['startDate'], now)
        endDate = min(args['endDate'], now)
        startDate = getBeginningOfDay(startDate)
        endDate = getEndOfDay(endDate)
        if endDate <= startDate:
            return []

        # convert start and end date to integer milliseconds for defining filters
        startDate = int(startDate*1000)
        endDate = int(endDate*1000)

        # compose filter for retrieval from ZEP
        create_filter_args = {
            'severity' : _severityGreaterThanOrEqual(SEVERITY_WARNING),
            'event_class' : args['eventClass'] +
                            ('/' if not args['eventClass'].endswith('/') else ''),
            'first_seen' : (0,endDate),
            'last_seen' : (startDate,),
            }
        event_filter = zep.createEventFilter(**create_filter_args)
        events = zep.getEventSummariesGenerator(event_filter)
        events_from_archive = zep.getEventSummariesGenerator(event_filter, archive=True)

        sum = defaultdict(int)
        counts = defaultdict(int)
        for evtsumm in chain(events, events_from_archive):

            first = evtsumm['first_seen_time']
            # if event is still open, downtime persists til end of report window
            if evtsumm['status'] not in CLOSED_EVENT_STATUSES:
                last = endDate
            else:
                last = evtsumm['status_change_time']

            # clip first and last within report time window
            first = max(first, startDate)
            last = min(last, endDate)

            # discard any events that have no elapsed time
            if first == last:
                continue

            # extract key fields, and update time/count tallies
            evt = evtsumm['occurrence'][0]
            evt_actor = evt['actor']
            device = evt_actor.get('element_identifier')
            component = evt_actor.get('element_sub_identifier')
            eventClass = evt['event_class']

            diff = last - first
            sum[(device, component, eventClass)] += diff
            counts[(device, component, eventClass)] += 1


        # Look up objects that correspond to the names
        report = []
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
            duration = Duration(seconds/1000)
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

