##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from .propertymap import DevicePropertyMap
from .dispatcher import BuildConfigTaskDispatcher
from .pollers import RelStorageInvalidationPoller
from .services import getConfigServices


class Constants(object):

    build_timeout_id = "zDeviceConfigBuildTimeout"
    pending_timeout_id = "zDeviceConfigPendingTimeout"
    time_to_live_id = "zDeviceConfigTTL"


__all__ = (
    "BuildConfigTaskDispatcher",
    "Constants",
    "DevicePropertyMap",
    "RelStorageInvalidationPoller",
    "getConfigServices",
)
