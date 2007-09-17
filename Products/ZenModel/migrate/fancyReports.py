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
from AccessControl import Permissions

class FancyReports(Migrate.Step):
    version = Migrate.Version(2, 1, 0)
    
    def cutover(self, dmd):
        
        # Build Reports/Fancy Reports
        frc = getattr(dmd.Reports, 'Multi-Graph Reports', None)
        if frc:
            if not isinstance(frc, FancyReportClass):
                frc.__class__ = FancyReportClass
        else:
            frc = FancyReportClass('Multi-Graph Reports')
            dmd.Reports._setObject(frc.id, frc)
        dmd.Reports.buildRelations()
        dmd.Reports['Multi-Graph Reports'].buildRelations()
        
        # Install sample fancy report?
        
        # Get rid of old Fancy Report menus
        reportList = getattr(dmd.zenMenus, 'Report_list')
        if hasattr(reportList, 'addFancyReport'):
            reportList.manage_deleteZenMenuItem(('addFancyReport',))
        reportList.manage_addZenMenuItem( 
                id='addFancyReport',
                description='Add Multi-Graph Report...', 
                action='dialog_addFancyReport', 
                permissions=('Change Device',), 
                isdialog=True, 
                allowed_classes=('FancyReportClass',),
                ordering=88.0)        
        
        if hasattr(dmd.zenMenus, 'collectionList'):
            dmd.zenMenus._delObject('collectionList')
        collectionList = dmd.zenMenus.manage_addZenMenu('collectionList')
        collectionList.manage_addZenMenuItem(
                id='addCollection',
                description='Add Collection...', 
                action='dialog_addCollection', 
                permissions=('Change Device',), 
                isdialog=True, 
                ordering=88.0)
        collectionList.manage_addZenMenuItem(
                id='deleteCollections',
                description='Delete Collections...', 
                action='dialog_deleteCollections', 
                permissions=('Change Device',), 
                isdialog=True, 
                ordering=87.0)

        if hasattr(dmd.zenMenus, 'collectionItemList'):
            dmd.zenMenus._delObject('collectionItemList')
        collectionList = dmd.zenMenus.manage_addZenMenu('collectionItemList')
        collectionList.manage_addZenMenuItem(
                id='deleteCollectionItems',
                description='Delete Items...', 
                action='dialog_deleteCollectionItems', 
                permissions=('Change Device',), 
                isdialog=True, 
                ordering=88.0)
        collectionList.manage_addZenMenuItem(
                id='resequenceCollectionItem',
                description='Re-sequence Items', 
                action="javascript:submitFormToMethod('collectionItemForm', 'manage_resequenceCollectionItems')", 
                permissions=('Change Device',), 
                isdialog=True, 
                ordering=87.0)

        if hasattr(dmd.zenMenus, 'GraphGroup_list'):
            dmd.zenMenus._delObject('GraphGroup_list')
        collectionList = dmd.zenMenus.manage_addZenMenu('GraphGroup_list')
        collectionList.manage_addZenMenuItem(
                id='addGraphGroup',
                description='Add Group...', 
                action='dialog_addGraphGroup', 
                permissions=('Change Device',), 
                isdialog=True, 
                ordering=89.0)
        collectionList.manage_addZenMenuItem(
                id='resequenceCollectionItem',
                description='Re-sequence Items', 
                action="javascript:submitFormToMethod('graphGroupForm', 'manage_resequenceGraphGroups')", 
                permissions=('Change Device',), 
                isdialog=True, 
                ordering=88.0)


FancyReports()
