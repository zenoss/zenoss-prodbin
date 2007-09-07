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
        
        # Build dmd.collections and dmd.graphDefs
        
        # Build Reports/Fancy Reports
        if not hasattr(dmd.Reports, 'Fancy Reports'):
            dmd.Reports.manage_addReportClass('Fancy Reports')
        
        # Install sample fancy report?
        
        # Install new menus
        dmd.buildMenus({  
            'Report_list': [ 
                {   'action': 'dialog_addFancyReport',
                    'allowed_classes': ('ReportClass',),
                    'description': 'Add Fancy Report...',
                    'id': 'addFancyReport',
                    'isdialog': True,
                    'ordering': 88.0,
                    'permissions': ('Change Device',),
                },
                ],
            'collectionList': [ 
                {   'action': 'dialog_addCollection',
                    'description': 'Add Collection',
                    'id': 'addCollection',
                    'isdialog': True,
                    'ordering': 88.0,
                    'permissions': ('Change Device',),
                },
                {   'action': 'dialog_deleteCollections',
                    'description': 'Delete Collections...',
                    'id': 'deleteCollections',
                    'isdialog': True,
                    'ordering': 88.0,
                    'permissions': ('Change Device',),
                },
                ]
            'GraphGroup_list': [ 
                {  'action': 'dialog_addGraphGroup',
                   'description': 'Add Group...',
                   'id': 'addGraphGroup',
                   'isdialog': True,
                   'ordering': 90.0,
                   'permissions': ('Change Device',)},
                {  'action': 'dialog_deleteGraphGroup',
                   'description': 'Delete Group...',
                   'id': 'deleteGraphGroup',
                   'isdialog': True,
                   'ordering': 90.0,
                   'permissions': ('Change Device',)},
                {  'action': "javascript:submitFormToMethod('graphGroupList', 'manage_resequenceGraphGroups')",
                   'description': 'Re-sequence Groups',
                   'id': 'resequenceGraphGroups',
                   'ordering': 80.0,
                   'permissions': ('Change Device',)}],
            })
                
            
        # RRDTemplate.graphDefs needs to be built
        numTemplates = 0
        numGraphs = 0
        numDataPoints = 0
        for template in dmd.Devices.getAllRRDTemplates():
            template.buildRelations()
            
            # Danger - testing only
            # Blow away all current graph definitions
            for graphDefId in template.graphDefs.objectIds():
                template.graphDefs._delObject(graphDefId)
                        
            if template.graphDefs():
                continue
            numTemplates += 1
            for rrdGraph in template.graphs():
                numGraphs += 1
                graphDef = GraphDefinition(rrdGraph.id)
                template.graphDefs._setObject(graphDef.id, graphDef)
                graphDef.sequence = rrdGraph.sequence
                graphDef.height = rrdGraph.height
                graphDef.width = rrdGraph.width
                graphDef.units = rrdGraph.units
                graphDef.log = rrdGraph.log
                graphDef.base = rrdGraph.base
                graphDef.summary = rrdGraph.summary
                graphDef.hasSummary = rrdGraph.hasSummary
                graphDef.miny = rrdGraph.miny
                graphDef.maxy = rrdGraph.maxy
                graphDef.custom = rrdGraph.custom
                isFirst = True
                for dsName in rrdGraph.dsnames:
                    dp = template.getRRDDataPoint(dsName)
                    gp = graphDef.manage_addDataPointGraphPoints([dsName], True)[0]                    
                    gp.color = dp.color
                    gp.lineType = dp.linetype or (isFirst and 'AREA') or 'LINE'
                    gp.stacked = dp.linetype != 'LINE'
                    gp.format = dp.format
                    gp.limit = dp.limit
                    gp.rpn = dp.rpn
                    isFirst = False
                    numDataPoints += 1
            # Remove the rrdGraphs
                


GraphReports()
