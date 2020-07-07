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

class IZenPackAdapterUpdatedDeviceEvent(IObjectEvent):
    pass

@implementer(IZenPackAdapterUpdatedDeviceEvent)
class ZenPackAdapterUpdatedDeviceEvent(ObjectEvent):
    pass

class IZenPackAdapterAddedDeviceEvent(IObjectEvent):
    pass

@implementer(IZenPackAdapterAddedDeviceEvent)
class ZenPackAdapterAddedDeviceEvent(ObjectEvent):
    pass

class IZenPackAdapterDeletedDeviceEvent(IObjectEvent):
    pass

@implementer(IZenPackAdapterDeletedDeviceEvent)
class ZenPackAdapterDeletedDeviceEvent(ObjectEvent):
    pass

onZenPackAdapterDeviceUpdate = _listener_decorator_factory(IZenPackAdapterUpdatedDeviceEvent)
onZenPackAdapterDeviceAdd = _listener_decorator_factory(ZenPackAdapterAddedDeviceEvent)
onZenPackAdapterDeviceDelete = _listener_decorator_factory(IZenPackAdapterDeletedDeviceEvent)
