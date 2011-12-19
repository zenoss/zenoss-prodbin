###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__='''
Migrate script that removes extra indexes that we do not need to catalog
to save time when cataloging devices and ip addresses
'''

__version__ = "$Revision$"[11:-2]

from Products.ZCatalog.Catalog import CatalogError
import Migrate

deviceSearchIndexes = ['getHWSerialNumber', 'getHWTag',
                       'getHWManufacturerName', 'getHWProductClass',
                       'getOSProductName', 'getOSManufacturerName',
                       'getPerformanceServerName', 'ipAddressAsInt',
                       'getProductionStateString', 'getPriorityString',
                       'getLocationName', 'getSystemNames', 'getDeviceGroupNames', 'allowedRolesAndUsers']


ipAddressIndexes = ['getInterfaceName', 'getDeviceName',
                    'getInterfaceDescription', 'getInterfaceMacAddress', 'allowedRolesAndUsers']

class DeviceSearchIpAddressCatalogCleanup(Migrate.Step):

    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        # device search
        cat = dmd.Devices.deviceSearch._catalog
        try:
            cat.delColumn('details')
        except ValueError:
            # already removed
            pass
        # remove
        for idx in deviceSearchIndexes:
            try:
                cat.delIndex(idx)
            except CatalogError:
                # already removed
                pass

        # networks
        for cat in (dmd.Networks.ipSearch._catalog, dmd.IPv6Networks.ipSearch._catalog):
            try:
                cat.delColumn('details')
            except ValueError:
                # already removed
                pass

            # remove indexes
            for idx in ipAddressIndexes:
                try:
                    cat.delIndex(idx)
                except CatalogError:
                    # already removed
                    pass

DeviceSearchIpAddressCatalogCleanup()
