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

from Products.ZenHub.HubService import HubService
from Products.ZenHub.services.ThresholdMixin import ThresholdMixin
from Products.ZenHub.PBDaemon import translateError

class EventService(HubService, ThresholdMixin):


    def __init__(self, dmd, instance):
        HubService.__init__(self, dmd, instance)
        self.config = self.dmd.Monitors.Performance._getOb(self.instance)
        self.methodPriorityMap = {
            'sendEvent': 0.0,
            'sendEvents': 0.0,
            }

    @translateError
    def remote_sendEvent(self, evt):
        try:
            return self.zem.sendEvent(evt)
        except Exception, ex:
            import logging
            log = logging.getLogger('log')
            log.exception(ex)


    @translateError
    def remote_sendEvents(self, evts):
        return self.zem.sendEvents(evts)


    @translateError
    def remote_getDevicePingIssues(self, *args, **kwargs):
        return self.zem.getDevicePingIssues(*args, **kwargs)


    @translateError
    def remote_getDeviceIssues(self, *args, **kwargs):
        return self.zem.getDeviceIssues(*args, **kwargs)


    @translateError
    def remote_getDefaultRRDCreateCommand(self):
        return self.config.getDefaultRRDCreateCommand()

    @translateError
    def remote_getDefaultPriority(self):
        return self.zem.defaultPriority

    @translateError
    def remote_oid2name(self, oid, exactMatch=True, strip=False):
        "get oids, even if we're handed slightly wrong values"
        name = self.dmd.Mibs.oid2name(oid, exactMatch, strip)
        return name or oid
