import xmlrpclib

s = xmlrpclib.ServerProxy('http://localhost:8081')
for i in range(100):
    s.sendEvent({
        'device':'eros',
        'eventClass':'xyzzy',
        'summary':'This is a test event',
        'severity':2,
        'component':'',
        })
