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

class AdminObjectMenus(Migrate.Step):
    version = Migrate.Version(2, 1, 0)

    def cutover(self, dmd):
        aolm = dmd.zenMenus.manage_addZenMenu('AdministeredObjects_list')
        aolm.manage_addZenMenuItem( action='dialog_addAdministeredDevice', 
            description='Add Device...', 
            id='addAdministeredDevice', 
            isdialog=True, 
            ordering=90.4, 
            permissions=('Manage DMD',))
        aolm.manage_addZenMenuItem( action='dialog_addAdministeredSystem', 
            description='Add System...', 
            id='addAdministeredSystem', 
            isdialog=True, 
            ordering=90.3, 
            permissions=('Manage DMD',))
        aolm.manage_addZenMenuItem( action='dialog_addAdministeredGroup', 
            description='Add Group...', 
            id='addAdministeredGroup', 
            isdialog=True, 
            ordering=90.2, 
            permissions=('Manage DMD',))
        aolm.manage_addZenMenuItem( action='dialog_addAdministeredLocation', 
            description='Add Location...', 
            id='addAdministeredLocation', 
            isdialog=True, 
            ordering=90.1, 
            permissions=('Manage DMD',))
        aolm.manage_addZenMenuItem( action='dialog_deleteAdministeredObjects', 
            description='Delete Administered Objects...', 
            id='deleteAdministeredObjects', 
            isdialog=True, 
            ordering=80.0, 
            permissions=('Manage DMD',))
        aolm.manage_addZenMenuItem( action='dialog_saveAdministeredObjects', 
            description='Save Administered Objects...', 
            id='saveAdministeredObjects', 
            isdialog=True, 
            ordering=85.0, 
            permissions=('Manage DMD',))  
        usm = dmd.zenMenus.manage_addZenMenu('UserSettings')
        usm.manage_addZenMenuItem( action='dialog_saveUserSettings', 
            description='Save User Settings...', 
            id='saveUserSettings', 
            isdialog=True, 
            ordering=0.0, 
            permissions=('Manage DMD',))


AdminObjectMenus()
