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

from twisted.spread import pb

from Products.ZenEvents.Event import Event
pb.setUnjellyableForClass(Event, Event)

from HubService import HubService

class EventService(HubService):

    def remote_sendEvent(self, evt):
        try:
            return self.zem.sendEvent(evt)
        except Exception, ex:
            import logging
            log = logging.getLogger('log')
            log.exception(ex)


    def remote_sendEvents(self, evts):
        return self.zem.sendEvents(evts)


    def remote_getDevicePingIssues(self, *args, **kwargs):
        return self.zem.getDevicePingIssues(*args, **kwargs)

    def remote_getWmiConnIssues(self):
        return self.zem.getWmiConnIssues()
