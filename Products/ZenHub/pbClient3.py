#! /usr/bin/python

from twisted.spread import pb
from twisted.internet import reactor
from twisted.cred import credentials
from socket import getfqdn

import Globals
from Products.ZenUtils.Driver import drive
from Products.ZenEvents.Event import Event

from zenhub import PB_PORT

class Listener(pb.Referenceable):

    def remote_beat(self, ts):
        import time
        print time.time() - ts

def error(reason):
    reason.printTraceback()
    reactor.stop()

def main():
    def go(driver):
        factory = pb.PBClientFactory()
        reactor.connectTCP("localhost", PB_PORT, factory)

        yield factory.login(credentials.UsernamePassword("zenoss", "zenoss"))
        perspective = driver.next()

        yield perspective.callRemote('getService', 'Beat', listener=Listener())
        service = driver.next()

    drive(go).addErrback(error)
    reactor.run()

main()
