##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from zope.dottedname.resolve import resolve

from Products.ZenHub.modelchange.configstore import (
    DeviceConfigStore,
    MonitorDeviceMapStore,
)

from ..task import requires, DMD, Abortable
from ..zenjobs import app


@app.task(
    bind=True,
    base=requires(DMD, Abortable),
    name="modelchange.build_device_config",
    summary="Create Device Configuration Task",
    description_template="Create the configuration for device {2}.",
    ignore_result=True,
)
def build_device_config(self, monitorname, configclassname, deviceid):
    """
    Create a configuration for the given device.

    @param monitorname: The name of the monitor/collector the device
        is a member of.
    @type monitorname: str
    @param configclassname: The fully qualified name of the class that
        will create the device configuration.
    @type configclassname: str
    @param deviceid: The ID of the device
    @type deviceid: str
    """
    svcconfigclass = resolve(configclassname)
    svcname = svcconfigclass.__name__

    cstore = DeviceConfigStore.make(svcname)
    mstore = MonitorDeviceMapStore.make(svcname)

    service = svcconfigclass(self.dmd, monitorname)
    configs = service.remote_getDeviceConfigs((deviceid,))
    if not configs:
        # No result means device was deleted or moved to another monitor.
        cstore.delete(monitorname, deviceid)
        mstore.remove(monitorname, deviceid)
    else:
        config = configs[0]
        cstore.set(monitorname, deviceid, config)
        mstore.add(monitorname, deviceid)
