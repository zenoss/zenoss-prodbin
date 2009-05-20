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

from Products.ZenUtils.ZenTales import talesEval, talesEvalStr
from Products.ZenModel.RRDDataPoint import getDataPointsByAliases
from Products.ZenModel.RRDDataPointAlias import EVAL_KEY
from Products.ZenReports import Utils, Utilization

class Column:
    def __init__(self, columnName, columnHandler=None):
        self._columnName = columnName
        self._columnHandler = columnHandler
        
    def getColumnName(self):
        return self._columnName
    
    def getValue(self, device, component=None, extra=None ):
        value = None
        if self._columnHandler is not None:
            value = self._columnHandler( device, component, extra )
        return value
                
def _fetchValueWithAlias( entity, datapoint, alias, summary  ):
    if alias:
        summary['extraRpn'] = alias.evaluate( entity ) 
    return entity.getRRDValue( datapoint.id, **summary )

        
class RRDColumn( Column ):
    def __init__(self, columnName, aliasName, columnHandler=None ):
        Column.__init__( self, columnName, columnHandler )
        self.aliasName = aliasName
    
    def getValue( self, device, component=None, extra=None ):
        summary=extra['summary']
        aliasDatapointPairs=extra['aliasDatapointPairs']
        value = None
        perfObject = component or device
        deviceTemplates = perfObject.getRRDTemplates()
        for alias, datapoint in aliasDatapointPairs:
            template = datapoint.datasource().rrdTemplate()
            if template in deviceTemplates:
                value = _fetchValueWithAlias( perfObject, datapoint, 
                                              alias, summary )
            if value is not None:
                break

        modifiedValue = value
        if self._columnHandler is not None:
            modifiedValue = self._columnHandler( device, 
                                                 component, 
                                                 value )
        return modifiedValue
     

class TalesColumnHandler:
    def __init__(self, talesExpression):
        self._talesExpression = 'python:%s' % talesExpression
    
    def __call__(self, device, component=None, extra=None, value=None ):
        kw=dict( device=device, component=component, value=value )
        if extra is not None:
            kw.update(extra)
        return talesEval( self._talesExpression, device, kw )

class AliasPlugin( object ):
    """
    A base class for performance report plugins that use aliases to 
    choose datapoints
    """ 
    def _getComponents(self, device, componentPath):
        componentPath='here/%s' % componentPath
        try:
            return talesEval( componentPath, device )
        except AttributeError:
            return []
        
    def getColumns(self):
        """
        Return the mapping of aliases to column names.  This should be one
        to one.  This is unimplemented in the base class.  
        """
        raise Exception( 'Unimplemented: Only subclasses of AliasPlugin' +
                         ' should be instantiated directly' )
        
    def getCompositeColumns(self):
        return []
    
    def getComponentPath(self):
        return None
    
    def run(self, dmd, args):
        """
        Generate the report using the columns and aliases obtained by
        calling getAliasColumnMap()
        """
        summary = Utilization.getSummaryArgs(dmd, args)
        
        def getAliasName( column ):
            return getattr( column, 'aliasName', None )
        
        columns = self.getColumns()
        nonAliasColumns = filter( lambda x: getAliasName( x ) is None, 
                                  columns )
        aliasColumns = filter( lambda x: getAliasName( x ) is not None,
                               columns )
        aliasColumnMap = dict( zip( map( getAliasName, aliasColumns ), 
                                    aliasColumns ) )
        
        columnDatapointsMap = {}

        for column in nonAliasColumns:
            columnDatapointsMap[column] = None
        
        aliasDatapointPairs = getDataPointsByAliases( dmd,
                                                      aliasColumnMap.keys() )
        for alias, datapoint in aliasDatapointPairs:
            if alias:
                column = aliasColumnMap[ alias.id ]
            else:
                column = aliasColumnMap[ datapoint.id ]
            
            if not columnDatapointsMap.has_key( column ):
                columnDatapointsMap[column]=[]
            columnDatapointsMap[column].append( (alias,datapoint) )

        report = []

        componentPath = self.getComponentPath()
        for device in Utilization.filteredDevices(dmd, args):
            columnValueMap = {}
            if componentPath is None:
                for column, aliasDatapointPairs in columnDatapointsMap.iteritems():
                    columnName = column.getColumnName()
                    extra=dict(aliasDatapointPairs=aliasDatapointPairs,
                               summary=summary)
                    value = column.getValue( 
                                    device=device,
                                    extra=extra )
                    columnValueMap[columnName] = value

                for column in self.getCompositeColumns():
                    val=column.getValue( device, extra=columnValueMap )
                    columnValueMap[column.getColumnName()]=val

                r = Utils.Record(device=device,
                                 **columnValueMap)
                report.append(r)
                
            else:
                components = self._getComponents( device,
                                                  componentPath )
                for component in components:
                    for column, aliasDatapointPairs in columnDatapointsMap.iteritems():
                        columnName = column.getColumnName()
                        extra=dict(aliasDatapointPairs=aliasDatapointPairs,
                                   summary=summary)
                        value = column.getValue(
                                    device=device, component=component,
                                    extra=extra )

                        columnValueMap[columnName] = value
                
                    for column in self.getCompositeColumns():
                        try:
                            val=column.getValue( device, component, 
                                                 extra=columnValueMap )
                        except TypeError:
                            val=None
                        except NameError:
                            val=None
                        columnValueMap[column.getColumnName()]=val
                            
                        
                    r = Utils.Record(device=device,
                                     component=component,
                                     **columnValueMap)
                    report.append(r)
                
        return report
    
