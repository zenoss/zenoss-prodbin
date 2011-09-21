###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__='''
This migration script adds indexes for fields displayed in the
device list.
'''

__version__ = "$Revision$"[11:-2]

from Products.ZCatalog.Catalog import CatalogError
from Products.ZenUtils.Search import makeCaseInsensitiveFieldIndex, makeCaseSensitiveKeywordIndex\
    ,makeCaseInsensitiveKeywordIndex

import Migrate

fieldIndexes = ['getHWSerialNumber', 'getHWTag',
                'getHWManufacturerName', 'getHWProductClass',
                'getOSProductName', 'getOSManufacturerName',
                'getPerformanceServerName', 'ipAddressAsInt',
                'getProductionStateString', 'getPriorityString',
                'getLocationName']

keywordIndexes = ['getSystemNames', 'getDeviceGroupNames']

class DeviceSearchCatalogUpdate(Migrate.Step):

    version = Migrate.Version(4, 0, 0)

    def cutover(self, dmd):
        devices = dmd.getDmdRoot('Devices')
        zcat = devices.deviceSearch
        # in version 3 to 4 (and 3.1 to 3.2) we changed how the path index was stored so
        # we will always need to reindex it
        idxs = ['path']
        # field indexes
        for indexName in fieldIndexes:
            try:
                zcat._catalog.addIndex(indexName, makeCaseInsensitiveFieldIndex(indexName))
                idxs.append(indexName)
            except CatalogError:
                pass

        # keyword indexes
        for indexName in keywordIndexes:
            try:
                zcat._catalog.addIndex(indexName, makeCaseInsensitiveKeywordIndex(indexName))
                idxs.append(indexName)
            except CatalogError:
                pass

        # permissions
        try:
            zcat._catalog.addIndex('allowedRolesAndUsers', makeCaseSensitiveKeywordIndex('allowedRolesAndUsers'))
            idxs.append('allowedRolesAndUsers')
        except CatalogError:
            pass
        # json in the meta data
        try:
            zcat.addColumn('details')
        except CatalogError:
            pass
        # populate the indexes
        for brain in zcat():
            try:
                brain.getObject().index_object(idxs=idxs, noips=True)
            except TypeError:
                # for upgrade the zenpacks may not have loaded the new code yet
                brain.getObject().index_object(noips=True)



DeviceSearchCatalogUpdate()
