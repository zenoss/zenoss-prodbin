###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import logging
import uuid
from zope.interface import implements
from zope.component import getUtility
from Products.Zuul.facades import ZuulFacade
from Products.Zuul.interfaces import ITriggersFacade
from Products.ZenMessaging.interfaces import ITriggersService, IProtobufJsonizable
import zenoss.protocols.protobufs.zep_pb2 as zep

log = logging.getLogger('zen.TriggersFacade')


class TriggersFacade(ZuulFacade):
    implements(ITriggersFacade)
    
    @property
    def triggers_service(self):
        return getUtility(ITriggersService)
        
    def getTriggers(self):
        trigger_set = self.triggers_service.getTriggers()
        return IProtobufJsonizable(trigger_set).json_friendly()

    def addTrigger(self, name):
        trigger = zep.EventTrigger()
        trigger.uuid = str(uuid.uuid4())
        trigger.name = name
        return self.triggers_service.addTrigger(trigger)

    def removeTrigger(self, uuid):
        trigger = zep.EventTrigger()
        trigger.uuid = uuid
        return self.triggers_service.removeTrigger(trigger)

    def getTrigger(self, uuid):
        trigger = self.triggers_service.getTrigger(uuid)
        return IProtobufJsonizable(trigger).json_friendly()
    
    def updateTrigger(self, **kwargs):
        trigger = zep.EventTrigger()
        IProtobufJsonizable(trigger).fill(kwargs)
        return self.triggers_service.updateTrigger(trigger)
    
    def parseFilter(self, source):
        return self.triggers_service.parseFilter(source)
    
    # This facade will also handle interactions with trigger subscriptions
    # and notifications.