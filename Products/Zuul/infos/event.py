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

from zope.interface import implements
from zope.component import adapts
from Products.Zuul.interfaces import IEventInfo
from Products.Zuul.interfaces import IEventEntity

class EventInfo(object):
    implements(IEventInfo)
    adapts(IEventEntity)

    def __init__(self, event):
        self._event = event

    @property
    def uid(self):
        return self._event.evid

    @property
    def severity(self):
        return self._event.severity

    @property
    def device(self):
        return self._event.device

    @property
    def component(self):
        return self._event.component

    @property
    def eventClass(self):
        return self._event.eventClass

    @property
    def summary(self):
        return self._event.summary

