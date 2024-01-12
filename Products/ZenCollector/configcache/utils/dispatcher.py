##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from ..task import build_device_config


class BuildConfigTaskDispatcher(object):
    """Encapsulates the act of dispatching the build_device_config task."""

    def __init__(self, configClasses):
        """
        Initialize a BuildConfigTaskDispatcher instance.

        The `configClasses` parameter should be the classes used to create
        the device configurations.

        @type configClasses: Sequence[Class]
        """
        self._sigs = {
            cls.__module__: build_device_config.s(
                ".".join((cls.__module__, cls.__name__))
            )
            for cls in configClasses
        }

    def dispatch_all(self, monitorid, deviceid, timeout):
        """
        Submit a task to build a device configuration from each
        configuration service.
        """
        soft_limit, hard_limit = _get_limits(timeout)
        for sig in self._sigs.values():
            sig.apply_async(
                (monitorid, deviceid),
                soft_time_limit=soft_limit,
                time_limit=hard_limit,
            )

    def dispatch(self, servicename, monitorid, deviceid, timeout):
        """
        Submit a task to build device configurations for the specified device.

        @type servicename: str
        @type monitorid: str
        @type deviceId: str
        """
        sig = self._sigs[servicename]
        if sig:
            soft_limit, hard_limit = _get_limits(timeout)
            sig.apply_async(
                (monitorid, deviceid),
                soft_time_limit=soft_limit,
                time_limit=hard_limit,
            )


def _get_limits(timeout):
    return timeout, (timeout + (timeout * 0.1))
