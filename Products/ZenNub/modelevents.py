##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.interface import implementer
from zope.component.interfaces import IObjectEvent, ObjectEvent

from Products.ZenHub.zodb import _listener_decorator_factory

class INubUpdatedDeviceEvent(IObjectEvent):
    pass

@implementer(INubUpdatedDeviceEvent)
class NubUpdatedDeviceEvent(ObjectEvent):
    pass

class INubAddedDeviceEvent(IObjectEvent):
    pass

@implementer(INubAddedDeviceEvent)
class NubAddedDeviceEvent(ObjectEvent):
    pass

class INubDeletedDeviceEvent(IObjectEvent):
    pass

@implementer(INubDeletedDeviceEvent)
class NubDeletedDeviceEvent(ObjectEvent):
    pass

onNubDeviceUpdate = _listener_decorator_factory(INubUpdatedDeviceEvent)
onNubDeviceAdd = _listener_decorator_factory(NubAddedDeviceEvent)
onNubDeviceDelete = _listener_decorator_factory(INubDeletedDeviceEvent)
