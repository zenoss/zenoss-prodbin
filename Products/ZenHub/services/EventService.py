#! /usr/bin/env python 
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from twisted.spread import pb

from Products.ZenEvents.Event import Event
pb.setUnjellyableForClass(Event, Event)

from zenoss.protocols.services import ServiceConnectionError
from Products.ZenHub.HubService import HubService
from Products.ZenHub.services.ThresholdMixin import ThresholdMixin
from Products.ZenHub.PBDaemon import translateError
from Products.Zuul import getFacade

import logging
log = logging.getLogger('zen.EventService')

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
            log.exception(ex)

    @translateError
    def remote_sendEvents(self, evts):
        return self.zem.sendEvents(evts)

    @translateError
    def remote_getDevicePingIssues(self, *args, **kwargs):
        zep = getFacade('zep')
        try:
            return zep.getDevicePingIssues()
        except ServiceConnectionError, e:
            # ZEN-503: Don't print a traceback in this case
            log.warn("Unable to contact ZEP.")
            return None

    @translateError
    def remote_getDeviceIssues(self, *args, **kwargs):
        zep = getFacade('zep')
        try:
            return zep.getDeviceIssues()
        except ServiceConnectionError, e:
            # ZEN-503: Don't print a traceback in this case
            log.warn("Unable to contact ZEP.")
            return None

    @translateError
    def remote_getDefaultRRDCreateCommand(self):
        return self.config.getDefaultRRDCreateCommand()

    @translateError
    def remote_getDefaultPriority(self):
        return self.zem.defaultPriority
