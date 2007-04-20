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
# This program is part of Zenoss Core, an open source monitoring platform.
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
# For complete information please visit: http://www.zenoss.com/oss/
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
