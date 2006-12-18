"The threshold report."

import time
import Globals
from Products.ZenUtils.Time import Duration
from Products.ZenReports.plugins import Plugin
dmd, args = Plugin.args(locals())

args.setdefault('startDate', (time.time() - 30*24*60*60))
args.setdefault('endDate', time.time())

report = []
w =  ' WHERE severity >= 3 '
w += ' AND lastTime > %(startDate)s '
w += ' AND firstTime <= %(endDate)s '
w += ' AND firstTime != lastTime '
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
try:
    e = c.cursor()
    print query
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
                except KeyError:
                    sum[(device, component, eventClass)] = diff
finally:
    c.close()
find = dmd.Devices.findDevice
totalTime = endDate - startDate
for (deviceName, componentName, eventClassName), seconds in sum.items():
    component = None
    eventClass = None
    device = find(deviceName)
    if device and componentName:
        for c in device.getMonitoredComponents():
            if c.name().find(componentName) >= 0:
                component = c
                break
    duration = Duration(seconds)
    percent = seconds * 100. / totalTime
    if component:
        print componentName, component, component.name()
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
                                seconds=seconds,
                                percentTime=percent,
                                duration=duration))
    
Plugin.pprint(report, locals())
