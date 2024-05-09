##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from ..constants import Constants


def get_ttl(device):
    return _getZProperty(
        device, Constants.time_to_live_id, Constants.time_to_live_value
    )


def get_minimum_ttl(device):
    return _getZProperty(
        device,
        Constants.minimum_time_to_live_id,
        Constants.minimum_time_to_live_value,
    )


def get_pending_timeout(device):
    return _getZProperty(
        device, Constants.pending_timeout_id, Constants.pending_timeout_value
    )


def get_build_timeout(device):
    return _getZProperty(
        device, Constants.build_timeout_id, Constants.build_timeout_value
    )


def _getZProperty(obj, propname, default):
    value = obj.getZ(propname)
    if value is None:
        return default
    return value
