###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################


import Migrate


class AddBackupFilesListMenu(Migrate.Step):
    version = Migrate.Version(2, 2, 0)


    def cutover(self, dmd):


        # Create the BackupFiles_list menu    
        dmd.buildMenus({  
            'BackupFiles_list': [ 
                {  'action': 'dialog_deleteBackup',
                   'description': 'Delete Backup...',
                   'id': 'deleteBackup',
                   'isdialog': True,
                   'ordering': 90.50,
                   'permissions': ('Change Device',)},
            ],
        })


AddBackupFilesListMenu()
