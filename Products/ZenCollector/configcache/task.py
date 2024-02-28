##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from datetime import datetime
from time import time

from zope.component import createObject
from zope.dottedname.resolve import resolve

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl

from Products.Jobber.task import requires, DMD, Abortable
from Products.Jobber.zenjobs import app

from .cache import ConfigKey, ConfigQuery, ConfigRecord, ConfigStatus
from .propertymap import DevicePropertyMap


@app.task(
    bind=True,
    base=requires(DMD, Abortable),
    name="configcache.build_device_config",
    summary="Create Device Configuration Task",
    description_template="Create the configuration for device {2}.",
    ignore_result=True,
)
def build_device_config(self, monitorname, deviceid, configclassname):
    """
    Create a configuration for the given device.

    @param monitorname: The name of the monitor/collector the device
        is a member of.
    @type monitorname: str
    @param deviceid: The ID of the device
    @type deviceid: str
    @param configclassname: The fully qualified name of the class that
        will create the device configuration.
    @type configclassname: str
    """
    svcconfigclass = resolve(configclassname)
    svcname = configclassname.rsplit(".", 1)[0]
    store = _getStore()
    key = ConfigKey(svcname, monitorname, deviceid)

    # Check whether this is an old job, i.e. job pending timeout.
    # If it is an old job, skip it, manager already sent another one.
    statuses = tuple(store.get_status(key))
    if statuses:
        key, status = statuses[0]
        if isinstance(status, ConfigStatus.Pending):
            pendinglimitmap = DevicePropertyMap.make_pending_timeout_map(
                self.dmd.Devices
            )
            now = time()
            uid = store.get_uid(key.device)
            duration = pendinglimitmap.get(uid)
            if status.submitted < (now - duration):
                return

    # Change the configuration's status from 'pending' to 'building' so
    # that configcache-manager doesn't prematurely timeout the build.
    store.set_building((ConfigKey(svcname, monitorname, deviceid), time()))
    self.log.info(
        "building device configuration  device=%s monitor=%s service=%s",
        deviceid,
        monitorname,
        svcname,
    )

    service = svcconfigclass(self.dmd, monitorname)
    configs = service.remote_getDeviceConfigs((deviceid,))
    if not configs:
        self.log.info(
            "no configuration built  device=%s monitor=%s service=%s",
            deviceid,
            monitorname,
            svcname,
        )
        key = next(
            store.search(
                ConfigQuery(
                    service=svcname, monitor=monitorname, device=deviceid
                )
            ),
            None,
        )
        if key is not None:
            # No result means device was deleted or moved to another monitor.
            store.remove(key)
            self.log.info(
                "removed previously built configuration  "
                "device=%s monitor=%s service=%s",
                key.device,
                key.monitor,
                key.service,
            )
    else:
        config = configs[0]
        uid = self.dmd.Devices.findDeviceByIdExact(deviceid).getPrimaryId()
        record = ConfigRecord.make(
            svcname, monitorname, deviceid, uid, time(), config
        )
        store.add(record)
        self.log.info(
            "added/replaced config  "
            "updated=%s device=%s monitor=%s service=%s",
            datetime.fromtimestamp(record.updated).isoformat(),
            deviceid,
            monitorname,
            svcname,
        )


class BuildConfigTaskDispatcher(object):
    """Encapsulates the act of dispatching the build_device_config task."""

    def __init__(self, configClasses):
        """
        Initialize a BuildConfigTaskDispatcher instance.

        The `configClasses` parameter should be the classes used to create
        the device configurations.

        @type configClasses: Sequence[Class]
        """
        self._classnames = {
            cls.__module__: ".".join((cls.__module__, cls.__name__))
            for cls in configClasses
        }

    def dispatch_all(self, monitorid, deviceid, timeout):
        """
        Submit a task to build a device configuration from each
        configuration service.
        """
        soft_limit, hard_limit = _get_limits(timeout)
        for name in self._classnames.values():
            build_device_config.apply_async(
                args=(monitorid, deviceid, name),
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
        name = self._classnames.get(servicename)
        if name is None:
            raise ValueError("service name '%s' not found" % servicename)
        soft_limit, hard_limit = _get_limits(timeout)
        build_device_config.apply_async(
            args=(monitorid, deviceid, name),
            soft_time_limit=soft_limit,
            time_limit=hard_limit,
        )


def _get_limits(timeout):
    return timeout, (timeout + (timeout * 0.1))


def _getStore():
    client = getRedisClient(url=getRedisUrl())
    return createObject("configcache-store", client)
