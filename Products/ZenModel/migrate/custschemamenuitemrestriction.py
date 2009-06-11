###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import Migrate

class CustomSchemaMenuRestriction(Migrate.Step):
    version = Migrate.Version(2, 5, 0)

    def cutover(self, dmd):
        dmd.Devices.buildMenus({
            'More': [ 
                      {  'action': 'editCustSchema',
                         'allowed_classes': ['DeviceClass'],
                         'description': 'Custom Schema',
                         'id': 'editCustSchema',
                         'ordering': 60.0,
                         'isglobal': True,
                         'permissions': ('Change Device',)},
            ]
        })
        try:
            dmd.zenMenus.More.zenMenuItems.editCustSchema.isglobal = True
        except AttributeError: 
            pass

CustomSchemaMenuRestriction()
