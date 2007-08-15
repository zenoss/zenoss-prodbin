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
from zenhub import PB_PORT

evt = Event()
evt.device = 'zenoss03'
evt.summary = 'sdfs pb event class'
evt.severity = 5
evt.eventClass = '/'


class RRDClient(pb.Referenceable):

    def __init__(self, value):
        self.value = value
    
    def run(self):
        factory = pb.PBClientFactory()
        reactor.connectTCP("localhost", PB_PORT, factory)
        d = factory.login(credentials.UsernamePassword("admin", "zenoss"),
                          client=self)
        d.addCallback(self.connected)
        d.addErrback(self.bad)
        reactor.run()


    def connected(self, perspective):
        print "got perspective ref:", perspective
        d = perspective.callRemote('getService', "RRDService", 'localhost', self)
        d.addCallback(self.sendValue)
        d.addErrback(self.bad)


    def sendValue(self, svc):
        self.svc = svc
        print "Sending value"
        d = self.svc.callRemote('writeRRD', 'localhost', None, None, 'MailTx_totalTime', self.value)
        d.addBoth(self.shutdown)


    def shutdown(self, unused):
        print unused
        reactor.stop()
        

    def bad(self, reason):
        print reason
        print 'error: '+str(reason.value)

   
    def remote_getName(self):
        return "RRDClient"


    def remote_shutdown(self, result):
        print result
        reactor.stop()

import sys
try:
    value = float(sys.argv[1])
except:
    print 'Unable to use value', sys.argv
    value = 20.
rc = RRDClient(value)
rc.run()
