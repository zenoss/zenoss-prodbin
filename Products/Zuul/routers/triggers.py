###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from operator import itemgetter
from Products import Zuul
from zope.component import getUtilitiesFor
from Products.ZenModel.interfaces import IAction
from Products.ZenUtils.Ext import DirectRouter
from Products.ZenUtils.extdirect.router import DirectResponse
from Products.Zuul.decorators import serviceConnectionError
from zenoss.protocols.protobufs.zep_pb2 import RULE_TYPE_JYTHON

import logging

log = logging.getLogger('zen.triggers');

class TriggersRouter(DirectRouter):
    """
    Router for Triggers UI section under Events.
    """

    def _getFacade(self):
        return Zuul.getFacade('triggers', self)

    @serviceConnectionError
    def getTriggers(self, **kwargs):
        return DirectResponse.succeed(data=self._getFacade().getTriggers())

    @serviceConnectionError
    def getTriggerList(self, **unused):
        return DirectResponse.succeed(data=self._getFacade().getTriggerList())

    @serviceConnectionError
    def addTrigger(self, newId):
        return DirectResponse.succeed(data=self._getFacade().addTrigger(newId))

    @serviceConnectionError
    def removeTrigger(self, uuid):
        return DirectResponse.succeed(msg="Trigger removed without a problem.", data=self._getFacade().removeTrigger(uuid))

    @serviceConnectionError
    def getTrigger(self, uuid):
        return DirectResponse.succeed(data=self._getFacade().getTrigger(uuid))

    @serviceConnectionError
    def updateTrigger(self, **data):
        data['rule']['api_version'] = 1
        data['rule']['type'] = RULE_TYPE_JYTHON
        response = self._getFacade().updateTrigger(**data)
        return DirectResponse.succeed(msg="Trigger updated without a problem.", data=response)

    @serviceConnectionError
    def parseFilter(self, source):
        try:
            response = self._getFacade().parseFilter(source)
            return DirectResponse.succeed(data=response)
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail(
                'Error parsing filter source. Please check your syntax.')


    # notification subscriptions
    @serviceConnectionError
    def getNotifications(self):
        response = self._getFacade().getNotifications()
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def addNotification(self, newId, action):
        response = self._getFacade().addNotification(newId, action)
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def removeNotification(self, uid):
        response = self._getFacade().removeNotification(uid)
        return DirectResponse.succeed(msg="Notification removed without a problem.", data=response)

    @serviceConnectionError
    def getNotificationTypes(self):
        utils = getUtilitiesFor(IAction)
        actionTypes = sorted((dict(id=id, name=util.name) for id, util in utils), key=itemgetter('id'))
        log.debug('notification action types are: %s' % actionTypes)
        return DirectResponse.succeed(data=actionTypes)

    @serviceConnectionError
    def getNotification(self, uid):
        response = self._getFacade().getNotification(uid)
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def updateNotification(self, **data):
        response = self._getFacade().updateNotification(**data)
        return DirectResponse.succeed(msg="Notification updated without a problem.", data=Zuul.marshal(response))

    @serviceConnectionError
    def getRecipientOptions(self):
        data = self._getFacade().getRecipientOptions()
        return DirectResponse.succeed(data=data);

    # subscription windows
    @serviceConnectionError
    def getWindows(self, uid):
        response = self._getFacade().getWindows(uid)
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def addWindow(self, contextUid, newId):
        response = self._getFacade().addWindow(contextUid, newId)
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def removeWindow(self, uid):
        response = self._getFacade().removeWindow(uid)
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def getWindow(self, uid):
        response = self._getFacade().getWindow(uid)
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def updateWindow(self, **data):
        response = self._getFacade().updateWindow(data)
        return DirectResponse.succeed(data=Zuul.marshal(response))
