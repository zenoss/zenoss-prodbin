from twisted.web import soap, xmlrpc, resource, server
import os

from ZenEvents.EventDatabase import EventDatabase

zeb = EventDatabase()

class XMLRPCEventDatabase(xmlrpc.XMLRPC):
    def xmlrpc_addevent(self, event):
        return zeb.addevent(event)
        
    def xmlrpc_deleteevent(self, event):
        return zeb.deleteevent(event)

    def xmlrpc_getEvents(self, lambdastr=""):
        return map(lambda x: x.getarray(),zeb.getEvents(lambdastr))
    
    def xmlrpc_getDeviceEvents(self, device):
        return map(lambda x: x.getarray(),zeb.getDeviceEvents(device))

    def xmlrpc_getRegexEvents(self, regex):
        return map(lambda x: x.getarray(),zeb.getRegexEvents(regex))


class SOAPEventDatabase(soap.SOAPPublisher):
    def soap_addevent(self, event):
        return zeb.addevent(event)

    def soap_deleteevent(self, oid):
        return zeb.deleteevent(oid)

    def soap_getEvents(self, lambdastr=""):
        return map(lambda x: x.getdict(),zeb.getEvents(lambdastr))
    
    def soap_getDeviceEvents(self, device):
        return map(lambda x: x.getdict(),zeb.getDeviceEvents(device))

    def soap_getRegexEvents(self, regex):
        return map(lambda x: x.getdict(),zeb.getRegexEvents(regex))



def main():
    from twisted.internet import reactor
    root = resource.Resource()
    root.putChild('XMLRPC', XMLRPCEventDatabase())
    root.putChild('SOAP', SOAPEventDatabase())
    reactor.listenTCP(7080, server.Site(root))
    reactor.run()

if __name__ == '__main__':
    main()
