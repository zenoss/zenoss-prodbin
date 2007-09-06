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

class ZenPackMenus(Migrate.Step):
    version = Migrate.Version(2, 1, 0)

    def cutover(self, dmd):  
        zpm = dmd.zenMenus.manage_addZenMenu('ZenPack')
        zpm.manage_addZenMenuItem( action='dialog_deletePackable', 
                                   description='Delete from ZenPack...', 
                                   id='deleteFromZenPack', 
                                   isdialog=True, 
                                   ordering=1.02, 
                                   permissions=('Manage DMD',))
        zpm.manage_addZenMenuItem( action='dialog_exportPack', 
                                  description='Export ZenPack...', 
                                  id='exportZenPack', 
                                  isdialog=True, 
                                  ordering=1.01, 
                                  permissions=('Manage DMD',))
        zplm = dmd.zenMenus.ZenPack_list
        zplm.manage_addZenMenuItem( action='dialog_deleteZenPacks', 
                                  description='Delete ZenPacks...', 
                                  id='deleteZenPack', 
                                  isdialog=True, 
                                  ordering=1.01, 
                                  permissions=('Manage DMD',))
                                   

ZenPackMenus()
