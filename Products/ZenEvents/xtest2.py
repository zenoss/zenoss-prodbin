from twisted.internet import reactor
from twisted.web import xmlrpc
import time

def main():
    t = xmlrpc.payloadTemplate
    if t.find('iso8859') < 0:
        xmlrpc.payloadTemplate = t.replace('?>', ' encoding="iso8859-1"?>')

    p = xmlrpc.Proxy('http://localhost:8081')
    d = p.callRemote('sendEvent',
                 dict(device='eros', 
                      eventClassKey = 'test',
                      eventClass = '/App',
                      summary='This is \xfc new test event: %d' % time.time(),
                      severity=4,
                      component='xyzzy'))

def printQuit(arg):
    print arg
    reactor.stop()

if __name__ == '__main__':
    main()
    reactor.run()
