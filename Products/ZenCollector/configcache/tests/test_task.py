##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import mock

from unittest import TestCase

from Products.Jobber.tests.utils import RedisLayer

from ..cache import CacheKey
from ..cache.storage import ConfigStore
from ..task import buildDeviceConfig

PATH = {
    "task": "Products.ZenCollector.configcache.task",
}


class TestBuildDeviceConfig(TestCase):

    layer = RedisLayer

    def setUp(t):
        t.device_name = "qadevice"
        t.device_uid = "/zport/dmd/Devices/Server/Linux/devices/qadevice"
        t.store = ConfigStore(t.layer.redis)

    def tearDown(t):
        del t.store

    @mock.patch("{task}.DevicePropertyMap".format(**PATH), autospec=True)
    @mock.patch("{task}.time".format(**PATH), autospec=True)
    @mock.patch("{task}.createObject".format(**PATH), autospec=True)
    @mock.patch("{task}.resolve".format(**PATH), autospec=True)
    def test_no_config_built(
        t, _resolve, _createObject, _time, _DevicePropertyMap
    ):
        monitor = "localhost"
        clsname = "Products.ZenHub.services.PingService.PingService"
        svcname = clsname.rsplit(".", 1)[0]
        submitted = 123456.34
        svcclass = mock.Mock()
        svc = mock.MagicMock()
        dmd = mock.Mock()
        log = mock.Mock()
        dvc = mock.Mock()
        key = CacheKey(svcname, monitor, t.device_name)

        _createObject.return_value = t.store
        _resolve.return_value = svcclass
        svcclass.return_value = svc
        svc.remote_getDeviceConfigs.return_value = []
        dmd.Devices.findDeviceByIdExact.return_value = dvc
        dvc.getPrimaryId.return_value = t.device_uid
        _time.return_value = submitted + 10
        limitmap = mock.Mock()
        _DevicePropertyMap.make_pending_timeout_map.return_value = limitmap
        limitmap.get.return_value = 1000

        t.store.set_pending((key, submitted))

        buildDeviceConfig(dmd, log, monitor, t.device_name, clsname, submitted)

        status = next(t.store.get_status(key), None)
        t.assertIsNone(status)
