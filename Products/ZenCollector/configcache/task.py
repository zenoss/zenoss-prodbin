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

from .cache import ConfigKey, ConfigQuery, ConfigRecord


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


def _getStore():
    client = getRedisClient(url=getRedisUrl())
    return createObject("configcache-store", client)
