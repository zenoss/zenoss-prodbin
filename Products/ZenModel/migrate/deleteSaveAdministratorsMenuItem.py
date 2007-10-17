###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information plaease visit: http://www.zenoss.com/oss/
#
###########################################################################
import Migrate

import Globals

import logging
log = logging.getLogger("zen.migrate")

from Products.ZenModel.ZenossSecurity import *

class DeleteSaveAdministratorsMenuItem(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):
        if hasattr(dmd.zenMenus.Administrator_list.zenMenuItems, 
            'saveAdministrators'):  
            dmd.zenMenus.Administrator_list.manage_deleteZenMenuItem(
                'saveAdministrators')
                                      
                                      
DeleteSaveAdministratorsMenuItem()
