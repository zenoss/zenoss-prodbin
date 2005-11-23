import Globals
from Products.ZenUtils.ZCmdBase import ZCmdBase
zodb = ZCmdBase(noopts=True)
zem = zodb.dmd.ZenEventManager

from Products.ZenEvents.Event import Event

evt = Event()
evt.device = "gate.confmon.loc"
evt.eventClass = "PingStatus"
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

