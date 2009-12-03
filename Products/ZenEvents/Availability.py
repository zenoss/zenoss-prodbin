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

import time

from Globals import InitializeClass
from Products.ZenUtils import Map
from Products.ZenEvents.ZenEventClasses import Status_Ping, Status_Snmp
from Products.ZenEvents.ZenEventClasses import Status_OSProcess

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

class Availability:
    security = ClassSecurityInfo()
    security.setDefaultAccess('allow')
    
    "Simple record for holding availability information"
    def __init__(self, device, component, downtime, total, systems=''):
        self.device = device
        self.systems = systems
        self.component = component

        # Guard against endDate being equal to or less than startDate.
        if total <= 0:
            self.availability = downtime and 0 or 1
        else:
            self.availability = max(0, 1 - (downtime / total))

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

class Report:
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
        self.severity = severity
        self.device = device
        self.component = component
        self.prodState = prodState
        self.manager = manager
        self.agent = agent
        self.DeviceClass = DeviceClass
        self.Location = Location
        self.System = System
        self.DeviceGroup = DeviceGroup
        self.DevicePriority = DevicePriority
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
        zem = dmd.ZenEventManager
        cols = 'device, component, firstTime, lastTime'
        endDate = self.endDate or time.time()
        startDate = self.startDate
        if not startDate:
            days = zem.defaultAvailabilityDays
            startDate = time.time() - days*60*60*24
        env = self.__dict__.copy()
        env.update(locals())
        w =  ' WHERE severity >= %(severity)s '
        w += ' AND lastTime > %(startDate)s '
        w += ' AND firstTime <= %(endDate)s '
        w += ' AND firstTime != lastTime '
        w += " AND eventClass = '%(eventClass)s' "
        w += " AND prodState >= %(prodState)s "
        if self.device:
            w += " AND device = '%(device)s' "
        if self.component:
            w += " AND component like '%%%(component)s%%' "
        if self.manager is not None:
            w += " AND manager = '%(manager)s' "
        if self.agent is not None:
            w += " AND agent = '%(agent)s' "
        if self.DeviceClass is not None:
            w += " AND DeviceClass = '%(DeviceClass)s' "
        if self.Location is not None:
            w += " AND Location = '%(Location)s' "
        if self.System is not None:
            w += " AND Systems LIKE '%%%(System)s%%' "
        if self.DeviceGroup is not None:
            w += " AND DeviceGroups LIKE '%%%(DeviceGroup)s%%' "
        if self.DevicePriority is not None:
            w += " AND DevicePriority = %(DevicePriority)s "
        if self.monitor is not None:
            w += " AND monitor = '%(monitor)s' "
        env['w'] = w % env
        s = ('SELECT %(cols)s FROM ( '
             ' SELECT %(cols)s FROM history %(w)s '
             '  UNION '
             ' SELECT %(cols)s FROM status %(w)s '
             ') AS U  ' % env)
                  
        devices = {}
        conn = zem.connect()
        try:
            curs = conn.cursor()
            curs.execute(s)
            while 1:
                rows = curs.fetchmany()
                if not rows: break
                for row in rows:
                    device, component, first, last = row
                    last = min(last, endDate)
                    first = max(first, startDate)
                    k = (device, component)
                    try:
                        devices[k] += last - first
                    except KeyError:
                        devices[k] = last - first
        finally: zem.close(conn)
        total = endDate - startDate
        if self.device:
            deviceList = []
            device = dmd.Devices.findDevice(self.device)
            if device:
                deviceList = [device]
                devices.setdefault( (self.device, self.component), 0)
        else:
            deviceList = []
            if not self.DeviceClass and not self.Location \
                and not self.System and not self.DeviceGroup:
                deviceList = dmd.Devices.getSubDevices()
            else:
                allDevices = {}
                for d in dmd.Devices.getSubDevices():
                    allDevices[d.id] = d

                deviceClassDevices = set()
                if self.DeviceClass:
                    try:
                        org = dmd.Devices.getOrganizer(self.DeviceClass)
                        for d in org.getSubDevices():
                            deviceClassDevices.add(d.id)
                    except KeyError:
                        pass
                else:
                    deviceClassDevices = set(allDevices.keys())

                locationDevices = set()
                if self.Location:
                    try:
                        org = dmd.Locations.getOrganizer(self.Location)
                        for d in org.getSubDevices():
                            locationDevices.add(d.id)
                    except KeyError:
                        pass
                else:
                    locationDevices = set(allDevices.keys())

                systemDevices = set()
                if self.System:
                    try:
                        org = dmd.Systems.getOrganizer(self.System)
                        for d in org.getSubDevices():
                            systemDevices.add(d.id)
                    except KeyError:
                        pass
                else:
                    systemDevices = set(allDevices.keys())

                deviceGroupDevices = set()
                if self.DeviceGroup:
                    try:
                        org = dmd.Groups.getOrganizer(self.DeviceGroup)
                        for d in org.getSubDevices():
                            deviceGroupDevices.add(d.id)
                    except KeyError:
                        pass
                else:
                    deviceGroupDevices = set(allDevices.keys())

                # Intersect all of the organizers.
                for deviceId in (deviceClassDevices & locationDevices & \
                    systemDevices & deviceGroupDevices):
                    deviceList.append(allDevices[deviceId])

            if not self.component:
                for d in dmd.Devices.getSubDevices():
                    devices.setdefault( (d.id, self.component), 0)
        deviceLookup = dict([(d.id, d) for d in deviceList])
        result = []
        for (d, c), v in devices.items():
            dev = deviceLookup.get(d, None)
            if dev is None:
                continue
            sys = dev.getSystemNamesString()
            result.append( Availability(d, c, v, total, sys) )
        # add in the devices that have the component, but no events
        if self.component:
            for d in deviceList:
                for c in d.getMonitoredComponents():
                    if c.name().find(self.component) >= 0:
                        a = Availability(d.id, c.name(), 0, total,
                            d.getSystemNamesString())
                        result.append(a)
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
