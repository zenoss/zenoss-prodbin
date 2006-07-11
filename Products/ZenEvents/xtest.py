import xmlrpclib

s = xmlrpclib.ServerProxy('http://localhost:8081')
ev = {  'device':'eros',
        'eventClass':'xyzzy',
        'summary':'This is a test event',
        'severity':2,
        'component':'',
        }
s.sendEvent(ev)
ev2 = ev.copy()
ev2['severity'] = 0
for i in range(10):
    s.sendEvents([ev, ev2])
issues = s.getDevicePingIssues()
for i in issues:
    print i
