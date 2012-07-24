##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


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
