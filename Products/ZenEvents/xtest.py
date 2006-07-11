import xmlrpclib

s = xmlrpclib.ServerProxy('http://localhost:8081')
ev = {  'device':'eros',
        'eventClass':'xyzzy',
        'summary':'This is a test event',
        'severity':2,
        'component':'',
        }
for i in range(100):
    s.sendEvents([ev, ev])
