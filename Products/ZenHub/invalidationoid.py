##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, 2023 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

# NOTE: this module exists to maintain compatibility with ZenPacks.

from .modelchange.oids import DefaultOidTransform, DeviceOidTransform

__all__ = ("DefaultOidTransform", "DeviceOidTransform")
