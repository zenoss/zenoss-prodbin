##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import argparse

from contextlib import closing
from time import sleep

from zope.component import getAdapter

from .configstore import makeDeviceConfigurationStore
from .interfaces import InvalidationPoller
from .services import getConfigServices
from .manager import InvalidationManager
from .zodb import getDB, dataroot


def app(args):
    _initialize_env()
    config_classes = getConfigServices()
    with closing(getDB(args.zodb_config_file)) as db:
        poller = getAdapter(db.storage, InvalidationPoller)
        with closing(db.open()) as session:
            with dataroot(session) as dmd:
                work(dmd, config_classes, poller)


def work(dmd, config_classes, poller):
    stores = {}
    for monitorname in dmd.Monitors.getPerformanceMonitorNames():
        for cls in config_classes:
            configsvc = cls(dmd, monitorname)
            svcname = configsvc.__module__
            dcs = makeDeviceConfigurationStore(svcname)
            configs = configsvc.remote_getDeviceConfigs()
            for config in configs:
                dcs[config.configId] = config
            stores[svcname] = dcs
            print(
                "Added %d configs for the %s config service"
                % (len(dcs), svcname)
            )

    print("Monitoring for changes")
    im = InvalidationManager(dmd, poller)
    while True:
        im.process_invalidations()
        sleep(1)


def _build_cli_args():
    parser = argparse.ArgumentParser(
        description="Monitors model changes to update device configurations.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--zodb-config-file",
        default="/opt/zenoss/etc/zodb.conf",
        help="ZODB connection config file.  If the file doesn't exist, "
        "the ZODB connection is created using /opt/zenoss/etc/globals.conf",
    )
    parser.set_defaults(func=app)
    return parser


def _initialize_env():
    from Zope2.App import zcml
    import Products.ZenHub
    import Products.ZenWidgets
    from OFS.Application import import_products
    from Products.ZenUtils.Utils import load_config, load_config_override
    from Products.ZenUtils.zenpackload import load_zenpacks

    import_products()
    load_zenpacks()
    zcml.load_site()
    load_config("modelchange.zcml", Products.ZenHub.modelchange)
    load_config_override("scriptmessaging.zcml", Products.ZenWidgets)


def main():
    parser = _build_cli_args()
    args = parser.parse_args()
    args.func(args)
