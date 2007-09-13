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
from Products.ZenModel.GraphDefinition import GraphDefinition
from Products.ZenModel.FancyReportClass import FancyReportClass

class FancyReports(Migrate.Step):
    version = Migrate.Version(2, 1, 0)
    
    def cutover(self, dmd):
        
        # Build Reports/Fancy Reports
        import pdb; pdb.set_trace()
        frc = getattr(dmd.Reports, 'Fancy Reports', None)
        if frc:
            if not isinstance(frc, FancyReportClass):
                frc.__class__ = FancyReportClass
        else:
            frc = FancyReportClass('Fancy Reports')
            dmd.Reports._setObject(frc.id, frc)
        dmd.Reports.buildRelations()
        dmd.Reports['Fancy Reports'].buildRelations()
        
        # Install sample fancy report?
        
        # Install new menus
        dmd.buildMenus({  
            'Report_list': [ 
                {   'action': 'dialog_addFancyReport',
                    'allowed_classes': ('FancyReportClass',),
                    'description': 'Add Fancy Report...',
                    'id': 'addFancyReport',
                    'isdialog': True,
                    'ordering': 88.0,
                    'permissions': ('Change Device',),
                },
                ],
            'collectionList': [ 
                {   'action': 'dialog_addCollection',
                    'description': 'Add Collection...',
                    'id': 'addCollection',
                    'isdialog': True,
                    'ordering': 88.0,
                    'permissions': ('Change Device',),
                },
                {   'action': 'dialog_deleteCollections',
                    'description': 'Delete Collections...',
                    'id': 'deleteCollections',
                    'isdialog': True,
                    'ordering': 87.0,
                    'permissions': ('Change Device',),
                },
                ],
            'collectionItemList': [ 
                {   'action': 'dialog_deleteCollectionItems',
                    'description': 'Delete Items...',
                    'id': 'deleteCollectionItems',
                    'isdialog': True,
                    'ordering': 88.0,
                    'permissions': ('Change Device',),
                },
                {  'action': "javascript:submitFormToMethod('collectionItemForm', 'manage_resequenceCollectionItems')",
                   'description': 'Re-sequence Items',
                   'id': 'resequenceCollectionItem',
                   'ordering': 87.0,
                   'permissions': ('Change Device',),
                },
                ],
            'GraphGroup_list': [ 
                {  'action': 'dialog_addGraphGroup',
                   'description': 'Add Group...',
                   'id': 'addGraphGroup',
                   'isdialog': True,
                   'ordering': 90.0,
                   'permissions': ('Change Device',)},
                {  'action': 'dialog_deleteGraphGroups',
                   'description': 'Delete Group...',
                   'id': 'deleteGraphGroups',
                   'isdialog': True,
                   'ordering': 89.0,
                   'permissions': ('Change Device',)},
                {  'action': "javascript:submitFormToMethod('graphGroupForm', 'manage_resequenceGraphGroups')",
                   'description': 'Re-sequence Groups',
                   'id': 'resequenceGraphGroups',
                   'ordering': 88.0,
                   'permissions': ('Change Device',)}],
        })


FancyReports()
