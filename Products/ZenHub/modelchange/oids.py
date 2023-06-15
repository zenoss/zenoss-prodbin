##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from zope.interface import implementer

from .interfaces import IInvalidationOid

log = logging.getLogger("zen.{}".format(__name__.split(".")[-1].lower()))


@implementer(IInvalidationOid)
class DefaultOidTransform(object):

    def __init__(self, obj):
        self._obj = obj

    def transformOid(self, oid):
        return oid


@implementer(IInvalidationOid)
class DeviceOidTransform(object):

    def __init__(self, obj):
        self._obj = obj

    def transformOid(self, oid):
        # get device oid
        result = oid
        device = getattr(self._obj, "device", lambda: None)()
        if device:
            result = device._p_oid
            log.debug(
                "oid for %s changed to device oid for %s", self._obj, device
            )
        return result
