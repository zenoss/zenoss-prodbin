##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """
Adds the availBlocks datasource to the FileSystem template. 
"""

import Migrate
import logging
#from Products.ZenModel.BasicDataSource import BasicDataSource
log = logging.getLogger('zen.migrate')


class addAvailBlocksDS(Migrate.Step):
    version = Migrate.Version(109, 0, 0)

    def cutover(self, dmd):
    
        template = getattr(dmd.Devices.Server.rrdTemplates, 'FileSystem', None)
        if template:
            availBlocks = template.manage_addRRDDataSource('availBlocks', 'BasicDataSource.SNMP')
            availBlocks.oid = '1.3.6.1.4.1.2021.9.1.7'
       

addAvailBlocksDS()
