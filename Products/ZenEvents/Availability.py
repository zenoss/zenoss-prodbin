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
    def __init__(self, device, component, downtime, total):
        self.device = device
        self.component = component
        self.availability = max(0, 1 - (downtime / total))

    def floatStr(self):
        return '%2.3f%%' % (self.availability * 100)

    def __str__(self):
        return self.floatStr()

    def __repr__(self):
        return '[%s %s %s]' % (self.device, self.component, self.floatStr())

    def __float__(self):
        return self.availability
    
    def __int__(self):
        return int(self.availability * 100)

    def __cmp__(self, other):
        return cmp((self.availability, self.device, self.component()),
                   (other.availability, other.device, other.component()))

    def getDevice(self, dmd):
        return dmd.Devices.findDevice(self.device)

    def getComponent(self, device):
        if device and self.component:
            return _findComponent(device, self.component)
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
                 component=''):
        self.startDate = _round(startDate)
        self.endDate = _round(endDate)
        self.eventClass = eventClass
        self.severity = severity
        self.device = device
        self.component = component


    def tuple(self):
        return (self.startDate, self.endDate, self.eventClass,
                self.severity, self.device, self.component)

    def __hash__(self):
        return hash(self.tuple())

    def __cmp__(self, other):
        return cmp(self.tuple(), other.tuple())


    def run(self, dmd):
        """Run the report, returning an Availability object for each device"""
        # Note: we don't handle overlapping "down" events, so down
        # time could get get double-counted.
        cols = 'device, component, firstTime, lastTime'
        endDate = self.endDate or time.time()
        startDate = self.startDate
        if not startDate:
            days = dmd.ZenEventManager.defaultAvailabilityDays
            startDate = time.time() - days*60*60*24
        env = self.__dict__.copy()
        env.update(locals())
        w =  ' WHERE severity >= %(severity)s '
        w += ' AND lastTime > %(startDate)s '
        w += ' AND firstTime <= %(endDate)s '
        w += ' AND firstTime != lastTime '
        w += " AND eventClass = '%(eventClass)s' "
        if self.device:
            w += " AND device = '%(device)s' "
        if self.component:
            w += " AND component like '%%%(component)s%%' "
        env['w'] = w % env
        s = ('SELECT %(cols)s FROM ( '
             ' SELECT %(cols)s FROM history %(w)s '
             '  UNION '
             ' SELECT %(cols)s FROM status %(w)s '
             ') AS U  ' % env)
        c = dmd.ZenEventManager.connect()
        devices = {}
        try:
            e = c.cursor()
            e.execute(s)
            while 1:
                rows = e.fetchmany()
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
        finally:
            c.close()
        total = endDate - startDate
        if self.device:
            deviceList = [dmd.Devices.findDevice(self.device)]
            devices.setdefault( (self.device, self.component), 0)
        else:
            deviceList = [d for d in dmd.Devices.getSubDevices()]
            if not self.component:
                for d in dmd.Devices.getSubDevices():
                    devices.setdefault( (d.id, self.component), 0)
        result = []
        for (d, c), v in devices.items():
            result.append( Availability(d, c, v, total) )
        # add in the devices that have the component, but no events
        if self.component:
            for d in deviceList:
                for c in d.getMonitoredComponents():
                    if c.name().find(self.component) >= 0:
                        a = Availability(d.id, c.name(), 0, total)
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
