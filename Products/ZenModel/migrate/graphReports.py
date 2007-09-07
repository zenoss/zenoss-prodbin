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

class GraphReports(Migrate.Step):
    version = Migrate.Version(2, 1, 0)
    

    def cutover(self, dmd):
        
        # Build Reports/Graph Reports
        if not hasattr(dmd.Reports, 'Graph Reports'):
            dmd.Reports.manage_addReportClass('Graph Reports')
        
        # Install sample GraphReport?
        
        # Build menus
        dmd.buildMenus({  
            'GraphReportElement_list': [ 
                {  'action': 'dialog_deleteGraphReportElement',
                   'description': 'Delete Graph...',
                   'id': 'deleteGraph',
                   'isdialog': True,
                   'ordering': 90.0,
                   'permissions': ('Change Device',)},
                {  'action': "javascript:submitFormToMethod('graphReportElementListform', 'manage_resequenceGraphReportElements')",
                   'description': 'Re-sequence Graphs',
                   'id': 'resequenceGraphs',
                   'ordering': 80.0,
                   'permissions': ('Change Device',)},
                ],
            'Report_list': [
                {   'action': 'dialog_addGraphReport',
                    'allowed_classes': ('ReportClass',),
                    'description': 'Add Graph Report...',
                    'id': 'addGraphReport',
                    'isdialog': True,
                    'ordering': 89.0,
                    'permissions': ('Change Device',)},
                {   'action': 'dialog_deleteReports',
                    'allowed_classes': ('ReportClass',),
                    'description': 'Delete Reports...',
                    'id': 'deleteDeviceReports',
                    'isdialog': True,
                    'ordering': 80.0,
                    'permissions': ('Change Device',)},
                {   'action': 'dialog_moveReports',
                    'allowed_classes': ('ReportClass',),
                    'description': 'Move Reports...',
                    'id': 'moveDeviceReports',
                    'isdialog': True,
                    'ordering': 70.0,
                    'permissions': ('Change Device',)},
                ]
            })


GraphReports()
