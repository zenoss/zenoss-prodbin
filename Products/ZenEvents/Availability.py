###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import time
from collections import defaultdict
from itertools import takewhile, chain

from Globals import InitializeClass
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.DeviceGroup import DeviceGroup
from Products.ZenModel.Location import Location
from Products.ZenModel.System import System
from Products.ZenUtils import Map
from Products.ZenEvents.ZenEventClasses import Status_Ping, Status_Snmp
from Products.ZenEvents.ZenEventClasses import Status_OSProcess
from Products.Zuul import getFacade
from Products.Zuul.interfaces import ICatalogTool
from Products.AdvancedQuery import Eq, Or, Not
from zenoss.protocols.protobufs.zep_pb2 import (SEVERITY_CRITICAL, SEVERITY_ERROR,
                                                SEVERITY_WARNING, SEVERITY_INFO,
                                                SEVERITY_DEBUG, SEVERITY_CLEAR)
from zenoss.protocols.protobufs.zep_pb2 import (STATUS_NEW, STATUS_ACKNOWLEDGED,
                                                STATUS_SUPPRESSED, STATUS_CLOSED,
                                                STATUS_CLEARED, STATUS_DROPPED,
                                                STATUS_AGED)

ALL_EVENT_STATUSES = set([STATUS_NEW, STATUS_ACKNOWLEDGED,
                        STATUS_SUPPRESSED, STATUS_CLOSED,
                        STATUS_CLEARED, STATUS_DROPPED,
                        STATUS_AGED])
CLOSED_EVENT_STATUSES = set([STATUS_CLOSED, STATUS_CLEARED,
                             STATUS_DROPPED, STATUS_AGED])
OPEN_EVENT_STATUSES = ALL_EVENT_STATUSES - CLOSED_EVENT_STATUSES

def _severityGreaterThanOrEqual(sev):
    """function to return a list of severities >= the given severity;
       defines severity priority using arbitrary order, instead of
       assuming numeric ordering"""
    severities_in_order = (SEVERITY_CRITICAL,
                           SEVERITY_ERROR,
                           SEVERITY_WARNING,
                           SEVERITY_INFO,
                           SEVERITY_DEBUG,
                           SEVERITY_CLEAR)
    return list(takewhile(lambda x : x != sev, severities_in_order)) + [sev,]

def _lookupUuid(catalog, cls, identifier):
    """function to retrieve uuid given an object's catalog, type, and identifier"""
    results = ICatalogTool(catalog).search(cls,
                                           query=Or(Eq('id', identifier),
                                                    Eq('name', identifier)),
                                           limit=1,
                                           uses_count=False)
    if results.total:
        return results.results.next().uuid

from AccessControl import ClassSecurityInfo

CACHE_TIME = 60.

_cache = Map.Locked(Map.Timed({}, CACHE_TIME))

def _round(value):
    if value is None: return None
    return (value // CACHE_TIME) * CACHE_TIME

def _findComponent(device, name):
    for c in device.getMonitoredComponents():
        if c.name() == name:
            return c
    return None

class Availability(object):
    security = ClassSecurityInfo()
    security.setDefaultAccess('allow')

    @staticmethod
    def getDefaultAvailabilityStart(dmd):
        return time.time() - dmd.ZenEventManager.defaultAvailabilityDays*24*60*60

    @staticmethod
    def getDefaultAvailabilityEnd():
        return time.time()

    # Simple record for holding availability information
    def __init__(self, device, component, downtime, total, systems=''):
        self.device = device
        self.systems = systems
        self.component = component

        # Guard against endDate being equal to or less than startDate.
        if total <= 0:
            self.availability = 0 if downtime else 1
        else:
            self.availability = max(0, 1 - (float(downtime) / total))

    def floatStr(self):
        return '%2.3f%%' % (self.availability * 100)

    def __str__(self):
        return self.floatStr()

    def __repr__(self):
        return '[%s %s %s]' % (self.device, self.component, self.floatStr())

    def __float__(self):
        return float(self.availability)
    
    def __int__(self):
        return int(self.availability * 100)

    def __cmp__(self, other):
        return cmp((self.availability, self.device, self.component()),
                   (other.availability, other.device, other.component()))

    def getDevice(self, dmd):
        return dmd.Devices.findDevice(self.device)

    def getComponent(self, dmd):
        if self.device and self.component:
            device = self.getDevice(dmd)
            if device:
                return _findComponent(device, self.component)
        return None

    def getDeviceLink(self, dmd):
        device = self.getDevice(dmd)
        if device:
            return device.getDeviceLink()
        return None

InitializeClass(Availability)

class Report(object):
    "Determine availability by counting the amount of time down"

    def __init__(self,
                 startDate = None,
                 endDate = None,
                 eventClass=Status_Ping,
                 severity=5,
                 device=None,
                 component='',
                 prodState=1000,
                 manager=None,
                 agent=None,
                 DeviceClass=None,
                 Location=None,
                 System=None,
                 DeviceGroup=None,
                 DevicePriority=None,
                 monitor=None):
        self.startDate = _round(startDate)
        self.endDate = _round(endDate)
        self.eventClass = eventClass
        self.severity = int(severity) if severity is not None else None
        self.device = device
        self.component = component
        self.prodState = int(prodState) if prodState is not None else None
        self.manager = manager
        self.agent = agent
        self.DeviceClass = DeviceClass
        self.Location = Location
        self.System = System
        self.DeviceGroup = DeviceGroup
        self.DevicePriority = int(DevicePriority) if DevicePriority is not None else None
        self.monitor = monitor

    def tuple(self):
        return (
            self.startDate, self.endDate, self.eventClass, self.severity,
            self.device, self.component, self.prodState, self.manager,
            self.agent, self.DeviceClass, self.Location, self.System,
            self.DeviceGroup, self.DevicePriority, self.monitor)

    def __hash__(self):
        return hash(self.tuple())

    def __cmp__(self, other):
        return cmp(self.tuple(), other.tuple())


    def run(self, dmd):
        """Run the report, returning an Availability object for each device"""
        # Note: we don't handle overlapping "down" events, so down
        # time could get get double-counted.
        __pychecker__='no-local'
        now = time.time()
        zep = getFacade("zep", dmd)
        endDate = self.endDate or Availability.getDefaultAvailabilityEnd()
        endDate = min(endDate, now)
        startDate = self.startDate
        if not startDate:
            startDate = Availability.getDefaultAvailabilityStart(dmd)

        # convert start and end date to integer milliseconds for defining filters
        startDate = int(startDate*1000)
        endDate = int(endDate*1000)
        total_report_window = endDate - startDate
        now_ms = int(now * 1000)

        create_filter_args = {
            'operator' : zep.AND,
            'severity' : _severityGreaterThanOrEqual(self.severity),
            'event_class' : self.eventClass +
                            ('/' if not self.eventClass.endswith('/') else '')
            }
        if self.device:
            create_filter_args['element_identifier'] = '"%s"' % self.device
        if self.component:
            create_filter_args['element_sub_identifier'] = '"%s"' % self.component
        if self.agent:
            create_filter_args['agent'] = self.agent
        if self.monitor is not None:
            create_filter_args['monitor'] = self.monitor

        # add filters on details
        filter_details = {}
        if self.DevicePriority is not None:
            filter_details['zenoss.device.priority'] = "%d:" % self.DevicePriority
        if self.prodState:
            filter_details['zenoss.device.production_state'] = "%d:" % self.prodState
        if filter_details:
            create_filter_args['details'] = filter_details

        # add filters on tagged values
        tag_uuids = []
        if self.DeviceClass:
            tag_uuids.append(_lookupUuid(dmd.Devices, DeviceClass, self.DeviceClass))
        if self.Location:
            tag_uuids.append(_lookupUuid(dmd.Locations, Location, self.Location))
        if self.System is not None:
            tag_uuids.append(_lookupUuid(dmd.Systems, System, self.System))
        if self.DeviceGroup is not None:
            tag_uuids.append(_lookupUuid(dmd.Groups, DeviceGroup, self.DeviceGroup))
        tag_uuids = filter(None, tag_uuids)
        if tag_uuids:
            create_filter_args['tags'] = tag_uuids

        # query zep for matching event summaries
        # 1. get all open events that:
        #    - first_seen < endDate
        #    (only need to check active events)
        # 2. get all closed events that:
        #    - first_seen < endDate
        #    - status_change > startDate
        #    (must get both active and archived events)

        # 1. get open events
        create_filter_args['first_seen'] = (0,endDate)
        create_filter_args['status'] = OPEN_EVENT_STATUSES
        event_filter = zep.createEventFilter(**create_filter_args)
        open_events = zep.getEventSummariesGenerator(event_filter)

        # 2. get closed events
        create_filter_args['status_change'] = (startDate+1,)
        create_filter_args['status'] = CLOSED_EVENT_STATUSES
        event_filter = zep.createEventFilter(**create_filter_args)
        closed_events = zep.getEventSummariesGenerator(event_filter)
        # must also get events from archive
        closed_events_from_archive = zep.getEventSummariesGenerator(event_filter, archive=True)

        # walk events, tallying up downtime
        accumulator = defaultdict(int)
        for evtsumm in chain(open_events, closed_events, closed_events_from_archive):

            first = evtsumm['first_seen_time']
            # if event is still open, downtime persists til end of report window
            if evtsumm['status'] not in CLOSED_EVENT_STATUSES:
                last = endDate
            else:
                last = evtsumm['status_change_time']

            # discard any events that have no elapsed time
            if first == last:
                continue

            # clip first and last within report time window
            first = max(first, startDate)
            last = min(last, endDate)

            evt = evtsumm['occurrence'][0]
            evt_actor = evt['actor']
            device = evt_actor.get('element_identifier')
            component = evt_actor.get('element_sub_identifier')

            # Only treat component specially if a component filter was specified.
            if self.component:
                accumKey = (device, component)
            else:
                accumKey = (device, '')

            accumulator[accumKey] += (last-first)

        if self.device:
            deviceList = []
            device = dmd.Devices.findDevice(self.device)
            if device:
                deviceList = [device]
                accumulator[(self.device, self.component)] += 0
        else:
            deviceList = []
            if (not self.DeviceClass and not self.Location and
                not self.System and not self.DeviceGroup):
                deviceList = dmd.Devices.getSubDevices()
            else:
                allDevices = dict((dev.id,dev) for dev in dmd.Devices.getSubDevices())
                allDeviceIds = set(allDevices.keys())

                def getOrgSubDevices(cat, orgId, allIds=allDeviceIds):
                    if orgId:
                        try:
                            org = cat.getOrganizer(orgId)
                        except KeyError:
                            pass
                        else:
                            return set(d.id for d in org.getSubDevices())
                    return allIds
                deviceClassDevices = getOrgSubDevices(dmd.Devices, self.DeviceClass)
                locationDevices    = getOrgSubDevices(dmd.Locations, self.Location)
                systemDevices      = getOrgSubDevices(dmd.Systems, self.System)
                deviceGroupDevices = getOrgSubDevices(dmd.Groups, self.DeviceGroup)

                # Intersect all of the organizers.
                deviceList.extend(allDevices[deviceId]
                                 for deviceId in (deviceClassDevices & locationDevices &
                                                       systemDevices & deviceGroupDevices))

            if not self.component:
                for dev in dmd.Devices.getSubDevices():
                    accumulator[(dev.id, '')] += 0

        # walk accumulator, generate report results
        deviceLookup = dict((dev.id, dev) for dev in deviceList)
        result = []
        lastdevid = None
        sysname = ''
        for (devid, compid), downtime in sorted(accumulator.items()):
            if devid != lastdevid:
                dev = deviceLookup.get(devid, None)
                if dev:
                    sysname = dev.getSystemNamesString()
                else:
                    sysname = ''
                lastdevid = devid
            result.append(Availability(devid, compid, downtime, total_report_window, sysname))

        # add in the devices that have the component, but no events - assume this means no downtime
        if self.component:
            downtime = 0
            for dev in deviceList:
                sysname = dev.getSystemNamesString()
                for comp in dev.getMonitoredComponents():
                    if self.component in comp.name():
                        result.append(Availability(dev.id, comp.name(), downtime, total_report_window, sysname))
        return result


def query(dmd, *args, **kwargs):
    r = Report(*args, **kwargs)
    try:
        return _cache[r.tuple()]
    except KeyError:
        result = r.run(dmd)
        _cache[r.tuple()] = result
        return result


if __name__ == '__main__':
    import pprint
    r = Report(time.time() - 60*60*24*30)
    start = time.time() - 60*60*24*30
    # r.component = 'snmp'
    r.component = None
    r.eventClass = Status_Snmp
    r.severity = 3
    from Products.ZenUtils.ZCmdBase import ZCmdBase
    z = ZCmdBase()
    pprint.pprint(r.run(z.dmd))
    a = query(z.dmd, start, device='gate.zenoss.loc', eventClass=Status_Ping)
    assert 0 <= float(a[0]) <= 1.
    b = query(z.dmd, start, device='gate.zenoss.loc', eventClass=Status_Ping)
    assert a == b
    assert id(a) == id(b)
    pprint.pprint(r.run(z.dmd))
    r.component = 'httpd'
    r.eventClass = Status_OSProcess
    r.severity = 4
    pprint.pprint(r.run(z.dmd))
    r.device = 'gate.zenoss.loc'
    r.component = ''
    r.eventClass = Status_Ping
    r.severity = 4
    pprint.pprint(r.run(z.dmd))
