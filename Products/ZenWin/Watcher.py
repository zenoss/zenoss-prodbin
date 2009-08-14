###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007-2009 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from pysamba.twisted.reactor import eventContext
from pysamba.wbem.Query import Query
from Products.ZenUtils.Driver import drive

import logging
log = logging.getLogger("zen.Watcher")

class Watcher:

    def __init__(self, device, query):
        self.wmi = Query()
        self.device = device
        self.queryString = query
        self.enum = None
        self.busy = False
        self.closeRequested = False
        log.debug("Starting watcher on %s", device.id)

    def connect(self):
        self.busy = True

        def finished(result):
            self.busy = False
            if self.closeRequested:
                self.close()
            return result

        def inner(driver):
            log.debug("connecting to %s", self.device.id)
            d = self.device

            yield self.wmi.connect(eventContext,
                                   d.id,
                                   d.manageIp,
                                   "%s%%%s" % (d.zWinUser, d.zWinPassword))
            driver.next()

            log.debug("connected to %s sending query", self.device.id)
            yield self.wmi.notificationQuery(self.queryString)

            self.enum = driver.next()
            log.debug("got query response from %s", self.device.id)

        return drive(inner).addBoth(finished)

    def getEvents(self, timeout=0, chunkSize=10):
        assert self.enum
        self.busy = True
        log.debug("Fetching events for %s", self.device.id)

        def fetched(result):
            log.debug("Events fetched for %s", self.device.id)
            return result

        def finished(result):
            self.busy = False
            if self.closeRequested:
                self.close()
            return result

        result = self.enum.fetchSome(timeoutMs=timeout, chunkSize=chunkSize)
        result.addBoth(finished)
        result.addCallback(fetched)
        return result

    def close(self):
        if self.busy:
            log.debug("close requested on busy WMI Query for %s; deferring",
                           self.device.id)
            self.closeRequesed = True
        elif self.wmi:
            log.debug("closing WMI Query for %s", self.device.id)
            self.wmi.close()
            self.wmi = None

