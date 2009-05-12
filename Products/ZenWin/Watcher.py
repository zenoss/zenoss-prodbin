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
log = logging.getLogger('zen.Watcher')

class Watcher:

    def __init__(self, device, query):
        log.debug('Starting watcher on %s', device.id)
        self.wmi = Query()
        self.device = device
        self.queryString = query
        self.enum = None

    def connect(self):
        name = self.device.id
        def inner(driver):
            try:
                log.debug('connecting to %s', name)
                d = self.device
                yield self.wmi.connect(eventContext,
                                       d.manageIp,
                                       '%s%%%s' % (d.zWinUser, d.zWinPassword))
                driver.next()
                log.debug('connected to %s sending query', name)
                yield self.wmi.notificationQuery(self.queryString)
                self.enum = driver.next()
                log.debug('got query response from %s', name)
            except Exception, ex:
                log.exception(ex)
                raise
        return drive(inner)

    def getEvents(self, timeout=0, chunkSize=10):
        assert self.enum
        name = self.device.id
        log.debug("Fetching events for %s", name)
        def fetched(result):
            log.debug("Events fetched for %s", name)
            return result
        try:
            result = self.enum.fetchSome(timeoutMs=timeout, chunkSize=chunkSize)
            result.addCallback(fetched)
            return result
        except Exception, ex:
            raise ex

    def close(self):
        self.wmi.close()
