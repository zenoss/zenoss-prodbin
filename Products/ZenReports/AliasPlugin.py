###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import Globals
from Products.ZenModel.RRDDataPoint import getDataPointsByAliases
from Products.ZenModel.RRDDataPointAlias import EVAL_KEY
from Products.ZenReports import Utils, Utilization


class AliasPlugin( object ):
    """
    A base class for performance report plugins that use aliases to 
    choose datapoints
    """ 
    
    def getAliasColumnMap(self):
        """
        Return the mapping of aliases to column names.  This should be one
        to one.  This is unimplemented in the base class.  
        """
        raise Exception( 'Unimplemented: Only subclasses of AliasPlugin' +
                         ' should be instantiated directly' )
    
    def run(self, dmd, args):
        """
        Generate the report using the columns and aliases obtained by
        calling getAliasColumnMap()
        """
        summary = Utilization.getSummaryArgs(dmd, args)
        
        aliasColumnMap = self.getAliasColumnMap()
        
        report = []
    
        columnDatapointsMap = {}
        aliasDatapointPairs = getDataPointsByAliases( dmd,
                                                      aliasColumnMap.keys() )
        for alias, datapoint in aliasDatapointPairs:
            if alias:
                columnName = aliasColumnMap[ alias.id ]
            else:
                columnName = aliasColumnMap[ datapoint.id ]
                            
            if not columnDatapointsMap.has_key( columnName ):
                columnDatapointsMap[columnName]=[]
            columnDatapointsMap[columnName].append( (alias,datapoint) )

        # @todo: Handle component reports
        for d in Utilization.filteredDevices(dmd, args):
            
            columnValueMap = {}
            for column, aliasDatapointPairs in columnDatapointsMap.iteritems():
                value = None
                for alias, datapoint in aliasDatapointPairs:
                    template = datapoint.datasource().rrdTemplate()
                    deviceTemplates = d.getRRDTemplates()
                    if template in deviceTemplates:
                        if alias:
                            summary['extraRpn'] = alias.evaluate( d ) 
                        value = d.getRRDValue( datapoint.id, **summary )
                    if value is not None:
                        break
                columnValueMap[column] = value

            r = Utils.Record(device=d,
                             **columnValueMap)
            report.append(r)
        
        return report
