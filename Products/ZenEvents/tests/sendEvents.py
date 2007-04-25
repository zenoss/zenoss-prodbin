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

import Globals
from Products.ZenUtils.ZCmdBase import ZCmdBase
zodb = ZCmdBase(noopts=True)
zem = zodb.dmd.ZenEventManager

from Products.ZenEvents.Event import Event
from Products.ZenEvents.ZenEventClasses import Status_Ping

evt = Event()
evt.device = "gate.confmon.loc"
evt.eventClass = Status_Ping
evt.summary = "device is down"
evt.severity = 5
zem.sendEvent(evt)

evt = Event()
evt.device = "gate.confmon.loc"
evt.eventClass = "TestEvent"
evt.summary = "this is a test event"
evt.severity = 3
evt.ntseverity = "info"
evt.ntsource = "Zope"
zem.sendEvent(evt)


