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

import Globals

from twisted.internet import reactor
from twisted.cred import credentials
from twisted.spread import pb

from Products.ZenEvents.Event import Event

evt = Event()
evt.device = 'zenoss03'
evt.summary = 'sdfs pb event class'
evt.severity = 5
evt.eventClass = '/'


class EventClient(pb.Referenceable):
    
    def run(self):
        factory = pb.PBClientFactory()
        reactor.connectTCP("localhost", 8789, factory)
        d = factory.login(credentials.UsernamePassword("test", "test"),client=self)
        d.addCallback(self.connected)
        d.addErrback(self.bad)
        reactor.run()

    def connected(self, perspective):
        print "got perspective ref:", perspective
        d = perspective.getService("EventService", self)
        d.addCallback(self.sendEvent)
        d.addErrback(self.bad)

    def sendEvent(self, svc):
        self.svc = svc
        d = self.svc.sendEvent(evt)
        d.addBoth(self.shutdown) 
        

    def bad(self, reason): 
        print 'error: '+str(reason.value)
   
    def remote_getName(self):
        return "EventClient"

    def remote_shutdown(self, result):
        print result
        reactor.stop()

ec = EventClient()
ec.run()


#event = {   
#    'device': 'zenoss02', 
#    'summary': 'test pb event', 
#    'severity': 5,
#    'eventClass': '/'
#}
#
#factory = pb.PBClientFactory()
#reactor.connectTCP("localhost", 8789, factory)
#d = factory.getRootObject()
#d.addCallback(lambda object: object.callRemote("sendEvent", event))
#d.addCallback(lambda object: object.callRemote("sendEvent", pbevt))
#def bad(reason): print 'error: '+str(reason.value)
#d.addErrback(bad)
#d.addCallback(lambda _: reactor.stop())
#reactor.run()

