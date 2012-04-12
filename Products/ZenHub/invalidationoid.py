###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import logging
from zope.interface import implements
from zope.component import adapts
from Products.ZenModel.DeviceComponent import DeviceComponent
from Products.ZenModel.DeviceHW import DeviceHW
from Products.ZenRelations.PrimaryPathObjectManager import PrimaryPathObjectManager
from Products.ZenHub.interfaces import IInvalidationOid

log = logging.getLogger('zen.InvalidationOid')


class DefaultOidTransform(object):
    implements(IInvalidationOid)
    adapts(PrimaryPathObjectManager)

    def __init__(self, obj):
        self._obj = obj

    def transformOid(self, oid):
        return oid

class DeviceOidTransform(object):
    implements(IInvalidationOid)

    def __init__(self, obj):
        self._obj = obj

    def transformOid(self, oid):
        #get device oid
        result = oid
        device = getattr(self._obj, 'device', lambda : None)()
        if device:
            result = device._p_oid
            log.debug("oid for %s changed to device oid for %s", self._obj, device )
        return result

