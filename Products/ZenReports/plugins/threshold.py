"The threshold report."

import time
import Globals
from Products.ZenUtils.Time import Duration
from Products.ZenReports.plugins import Plugin
dmd, args = Plugin.args(locals())
zem = dmd.ZenEventManager

def dateAsFloat(args, key, default):
    from Products.ZenUtils.Time import ParseUSDate
    if args.has_key(key):
        args[key] = ParseUSDate(args[key])
    else:
        args[key] = default

dateAsFloat(args, 'startDate', (time.time() - zem.defaultAvailabilityDays*24*60*60))
dateAsFloat(args, 'endDate', time.time())
eventClass = args.get('eventClass', '')


# Get all the threshold related events from summary and history

report = []
w =  ' WHERE severity >= 3 '
w += ' AND lastTime > %(startDate)s '
w += ' AND firstTime <= %(endDate)s '
w += ' AND firstTime != lastTime '
if eventClass:
    w += " AND eventClass = '%s' " % eventClass
else:
    w += " AND eventClass like '/Perf/%%' "

args['cols'] = 'device, component, eventClass,  firstTime, lastTime '
w %= args
args['w'] = w
query = ('SELECT %(cols)s FROM ( '
         ' SELECT %(cols)s FROM history %(w)s '
         '  UNION '
         ' SELECT %(cols)s FROM status %(w)s '
         ') AS U ' % args)
c = dmd.ZenEventManager.connect()
sum = {}
counts = {}
try:
    e = c.cursor()
    e.execute(query)
    startDate = args['startDate']
    endDate = args['endDate']
    while 1:
        rows = e.fetchmany()
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
finally:
    c.close()
    
# Look up objects that correspond to the names
find = dmd.Devices.findDevice
totalTime = endDate - startDate
for k, seconds in sum.items():
    deviceName, componentName, eventClassName = k
    component = None
    eventClass = None
    device = find(deviceName)
    if device and componentName:
        for c in device.getMonitoredComponents():
            if c.name().find(componentName) >= 0:
                component = c
                break
    # get some values useful for the report
    duration = Duration(seconds)
    percent = seconds * 100. / totalTime
    try:
        eventClass = dmd.Events.getOrganizer(eventClassName)
    except KeyError:
        pass
    report.append(Plugin.Record(deviceName=deviceName,
                                device=device,
                                componentName=componentName,
                                component=component,
                                eventClassName=eventClassName,
                                eventClass=eventClass,
                                count=counts.get(k, 1),
                                seconds=seconds,
                                percentTime=percent,
                                duration=duration))
    
Plugin.pprint(report, locals())
