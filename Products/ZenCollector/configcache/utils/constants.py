##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


class Constants(object):

    build_timeout_id = "zDeviceConfigBuildTimeout"
    pending_timeout_id = "zDeviceConfigPendingTimeout"
    time_to_live_id = "zDeviceConfigTTL"
    minimum_time_to_live_id = "zDeviceConfigMinimumTTL"

    # Default values
    build_timeout_value = 7200
    pending_timeout_value = 7200
    time_to_live_value = 43200
    minimum_time_to_live_value = 0
