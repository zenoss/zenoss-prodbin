##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = '''
Create relations between device and Ip Address under Network
'''

import Migrate
import logging
log = logging.getLogger("zen.migrate")
from Products.Zuul.interfaces import ICatalogTool
from Products.ZenModel.IpAddress import IpAddress
from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION


class addDeviceIpAddrRelation(Migrate.Step):
    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def cutover(self, dmd):
        log.info("Updating relationships on Devices")
        for dev in dmd.Devices.getSubDevices():
            try:
                dev.buildRelations()
            #some objects can fail relations building process
            except (Exception,):
                continue

        log.info("Updating relationships on Ip Addresses")
        catalog = ICatalogTool(dmd.Networks)
        for ip in catalog.search(IpAddress):
            try:
                ip.getObject().buildRelations()
            #some objects can fail relations building process
            except (Exception,):
                continue


addDeviceIpAddrRelation()

