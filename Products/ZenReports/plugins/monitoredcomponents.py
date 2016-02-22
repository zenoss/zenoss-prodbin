##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import transaction
from Products.AdvancedQuery import Eq
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.ZenReports.AliasPlugin import AliasPlugin
from Products.ZenReports import Utils

class monitoredcomponents(AliasPlugin):
    """
    Fetches every component in the system. Returns a generator of
    dictionaries with metadata about each component so we can quickly invalidate
    the component.
    This keeps the memory usage in check.
    """

    def getSubComponents(self, dmd):
        i = 0
        catalog = IModelCatalogTool(dmd.Devices)
        COMPONENT = 'Products.ZenModel.DeviceComponent.DeviceComponent'
        query = Eq('monitored', '1')
        for brain in catalog.search(COMPONENT, query=query):
            i += 1
            obj = None
            try:
                obj = brain.getObject()
            except KeyError:
                continue
            dev = obj.device()
            status = obj.getStatus()
            row = (dict(
                    getParentDeviceTitle=obj.getParentDeviceTitle(),
                    hostname=obj.getParentDeviceTitle(),
                    name=obj.name(),
                    meta_type=obj.meta_type,
                    getInstDescription=obj.getInstDescription(),
                    getStatusString=obj.convertStatus(status),
                    getDeviceLink=obj.getDeviceLink(),
                    getPrimaryUrlPath=obj.getPrimaryUrlPath(),
                    cssclass=obj.getStatusCssClass(status),
                    status=status
                    ))
            obj._p_invalidate()
            dev._p_invalidate()
            if i % 100 == 0:
                transaction.abort()
            yield Utils.Record(**row)

    def run(self, dmd, args):
        return self.getSubComponents(dmd)
