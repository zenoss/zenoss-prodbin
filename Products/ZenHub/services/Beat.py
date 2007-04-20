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
#! /usr/bin/env python 

from HubService import HubService
from twisted.internet import reactor
from twisted.spread import pb
import time

class Beat(HubService):

    def __init__(self, dmd, instance):
        HubService.__init__(self, dmd, instance)
        self.beat()

    def beat(self):
        secs = time.time()
        for listener in self.listeners:
            d = listener.callRemote('beat', secs)
            d.addErrback(self.error)
        reactor.callLater(1, self.beat)

    def error(self, reason, listener):
        reason.printTraceback()
        
