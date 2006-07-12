import xmlrpclib
import time

s = xmlrpclib.ServerProxy('http://localhost:8081')

event = dict(device='eros', 
             eventClass='/Unknown',
             summary='This is a test event: %d' % time.time(), 
             severity=3,
             component='xyzzy')
clear = ev.copy()
clear.update(dict(severity=0, summary="All better now!"))

def main():
    "perormance test"
    for i in range(100):
        s.sendEvents([event, clear])

def coverage():
    s.sendEvents([event, clear])
    s.sendEvent(event)
    issues = s.getDevicePingIssues()
    for i in issues:
        print i

def simple():
    s.sendEvent(event)
    time.sleep(10)
    s.sendEvent(clear)

simple()
