#! /usr/bin/python

from twisted.spread import pb
from twisted.internet import reactor
from twisted.cred import credentials
from socket import getfqdn

import Globals
from Products.ZenUtils.Driver import drive
from Products.ZenEvents.Event import Event

from zenhub import PB_PORT

def main():
    def go(driver):
        factory = pb.PBClientFactory()
        reactor.connectTCP("localhost", PB_PORT, factory)

        yield factory.login(credentials.UsernamePassword("zenoss", "zenoss"))
        perspective = driver.next()

        yield perspective.callRemote('getService', 'EventService', 'client1')
        service = driver.next()

        service.sendEvent(Event(device=getfqdn(),
                                summary="This is a test",
                                severity=5))

    drive(go).addBoth(lambda x: reactor.stop())
    reactor.run()

main()
