##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function

import argparse

from contextlib import closing
from time import sleep

import transaction

from MySQLdb import OperationalError
from zope.component import getAdapter

from .configstore import DeviceConfigStore, MonitorDeviceMapStore
from .interfaces import InvalidationPoller
from .services import getConfigServices
from .manager import InvalidationManager
from .zodb import getDB, dataroot


def app(args):
    _initialize_env()
    while True:
        try:
            with closing(getDB(args.zodb_config_file)) as db:
                poller = getAdapter(db.storage, InvalidationPoller)
                with closing(db.open()) as session:
                    try:
                        with dataroot(session) as dmd:
                            work(dmd, poller)
                    finally:
                        transaction.abort()
        except OperationalError as oe:
            print("Lost database connection: %s" % (oe,))
            pass
        else:
            break


def work(dmd, poller):
    print("Creating configurations and writing them to Redis")
    configClasses = getConfigServices()
    monitorStore, configStores = create_stores(configClasses)
    configServices = load_configs(  # noqa F821
        dmd, configClasses, monitorStore, configStores
    )
    print("Monitoring for changes")
    im = InvalidationManager(dmd, poller)
    while True:
        updates = im.poll()
        if updates:
            print(updates)
        sleep(1)


def create_stores(configClasses):
    configStores = {
        cls.__name__: DeviceConfigStore.make(cls)
        for cls in configClasses
    }
    monitorStore = MonitorDeviceMapStore.make()
    return monitorStore, configStores


def load_configs(dmd, configClasses, monitorStore, configStores):
    configServices = {}
    for monitorname in dmd.Monitors.getPerformanceMonitorNames():
        for cls in configClasses:
            configsvc = cls(dmd, monitorname)
            svcname = cls.__name__
            configServices[(monitorname, svcname)] = configsvc
            dcs = configStores[svcname]
            configs = configsvc.remote_getDeviceConfigs()
            for config in configs:
                dcs[config.configId] = config
                monitorStore.add(monitorname, svcname, config.configId)
            print(
                "Added %d configs for the %s config service"
                % (len(dcs), svcname)
            )
    return configServices


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


def main():
    parser = _build_cli_args()
    args = parser.parse_args()
    args.func(args)
