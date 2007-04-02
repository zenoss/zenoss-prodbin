#! /usr/bin/python

from twisted.spread import pb
from twisted.internet import reactor
from twisted.cred import credentials

import Globals
from Products.ZenUtils.Driver import drive

import zenhub

def main():
    def go(driver):
        factory = pb.PBClientFactory()
        reactor.connectTCP("localhost", zenhub.PB_PORT, factory)
        
        yield factory.login(credentials.UsernamePassword("zenoss", "zenoss"))
        perspective = driver.next()
        print 'got perspective', perspective

        yield perspective.callRemote('getService', 'EventService', 'client1')
        service = driver.next()
        print 'got service', service

    drive(go).addBoth(lambda x: reactor.stop())
    reactor.run()

main()
