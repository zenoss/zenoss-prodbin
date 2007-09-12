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
from Products.ZenModel.ConfigurationError import ConfigurationError

class GraphDefinitionsAndFriends(Migrate.Step):
    version = Migrate.Version(2, 1, 0)
    
    def __init__(self):
        Migrate.Step.__init__(self)
        import thresholds
        self.dependencies = [thresholds.thresholds]


    def cutover(self, dmd):
        
        # Build Reports/Fancy Reports
        if not hasattr(dmd.Reports, 'Graph Reports'):
            dmd.Reports.manage_addReportClass('Graph Reports')
        
        # Install sample fancy report?
        
        # Install new menus
        dmd.buildMenus({  
            'GraphPoint_list': [ 
                {  'action': 'dialog_addDataPointGraphPoint',
                   'description': 'Add DataPoint...',
                   'id': 'addGPFromDataPoint',
                   'isdialog': True,
                   'ordering': 90.50,
                   'permissions': ('Change Device',)},
                {  'action': 'dialog_addThresholdGraphPoint',
                   'description': 'Add Threshold...',
                   'id': 'addGPFromThreshold',
                   'isdialog': True,
                   'ordering': 90.49,
                   'permissions': ('Change Device',)},
                {  'action': 'dialog_addCustomGraphPoint',
                   'description': 'Add Custom...',
                   'id': 'addGPCustom',
                   'isdialog': True,
                   'ordering': 90.49,
                   'permissions': ('Change Device',)},
                {  'action': 'dialog_deleteGraphPoint',
                   'description': 'Delete GraphPoint...',
                   'id': 'deleteGraphPoint',
                   'isdialog': True,
                   'ordering': 90.0,
                   'permissions': ('Change Device',)},
                {  'action': "javascript:submitFormToMethod('graphPointList', 'manage_resequenceGraphPoints')",
                   'description': 'Re-sequence GraphPoints',
                   'id': 'resequenceGraphPoints',
                   'ordering': 80.0,
                   'permissions': ('Change Device',)}
            ],
            })

            
        # RRDTemplate.graphDefs needs to be built
        numTemplates = 0
        numGraphs = 0
        numDataPointsFound = 0
        numDataPointsMissing = 0
        for template in dmd.Devices.getAllRRDTemplates():
            template.buildRelations()
                        
            if template.graphDefs():
                continue

            numTemplates += 1
            for rrdGraph in template.graphs():
                numGraphs += 1
                graphDef = GraphDefinition(rrdGraph.id)
                template.graphDefs._setObject(graphDef.id, graphDef)
                graphDef = getattr(template.graphDefs, graphDef.id)
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
                    try:
                        dp = template.getRRDDataPoint(dsName)
                        numDataPointsFound += 1
                    except ConfigurationError:
                        dp = None
                        numDataPointsMissing += 1
                    includeThresholds = not graphDef.custom                     
                    gp = graphDef.manage_addDataPointGraphPoints(
                                        [dsName], includeThresholds)[0]
                    if dp:
                        gp.color = dp.color
                        if graphDef.custom:
                            gp.lineType = ''
                        else:
                            gp.lineType = dp.linetype or \
                                            (isFirst and 'AREA') or 'LINE'
                        gp.stacked = dp.linetype != 'LINE'
                        gp.format = dp.format
                        gp.limit = dp.limit
                        gp.rpn = dp.rpn
                    isFirst = False
            # Remove the rrdGraphs
            # Keep them for now, remove in 2.2
            #for graphId in template.graphs.objectIds():
            #    template.graphs._delObject(graphId)
            
        print('processed %s templates, %s graphs, %s datapoints found, '
                '%s datapoints missing' % 
                (numTemplates, numGraphs, 
                numDataPointsFound, numDataPointsMissing))
                

GraphDefinitionsAndFriends()
