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
__doc__="""AliasPlugin

In order to more easily create reports, there is now a base class (AliasPlugin)
that plugins can subclass and provide minimal information.  The plugin is
meant to be run from an rpt file.
"""
import Globals

from Products.ZenUtils.ZenTales import talesEval, talesEvalStr
from Products.ZenModel.RRDDataPoint import getDataPointsByAliases
from Products.ZenModel.RRDDataPointAlias import EVAL_KEY
from Products.ZenReports import Utils, Utilization

class Column( object ):
    """
    Represents a column in a report row.  Returns a value when given the
    context represented by the row.  For example, a brain-dead report
    might list the paths of all the devices in the system.  A Column object
    that represents the path column would know how to return the path given
    the device.
    """
    def __init__(self, columnName, columnHandler=None):
        """
        @param columnName: the name of the column
        @param columnHandler: optional object or method that knows
                              how to take the row context and return
                              the column value
        """
        self._columnName = columnName
        self._columnHandler = columnHandler

    def getColumnName(self):
        return self._columnName

    def getValue(self, device, component=None, extra=None ):
        """
        @param device: the device represented by this row
        @param component: the component represented by this row (if present)
        @param extra: extra context passed to the columnHandler that will
                      generate the column value
        """
        value = None
        if self._columnHandler is not None:
            value = self._columnHandler( device, component, extra )
        return value

    def getAliasName(self):
        """
        @return the alias that this column uses (if any)
        """
        # This ugly type-check is needed for performance.  We
        # gather up aliases so we can get all the necessary datapoints
        # at one time.
        return getattr( self._columnHandler, 'aliasName', None )

def _fetchValueWithAlias( entity, datapoint, alias, summary  ):
    """
    Generates the alias RPN formula with the entity as the context, then
    retrieves the RRD value of the datapoint with the RPN formula
    """
    if alias:
        summary['extraRpn'] = alias.evaluate( entity )
    return entity.getRRDValue( datapoint.id, **summary )


class RRDColumnHandler( object ):
    """
    A handler that return RRD data for the value given the row context
    """
    def __init__(self, aliasName ):
        """
        @param aliasName: the alias or datapoint name to fetch
        @param columnHandler: optional columnHandler method or object
                       for post-processing of the RRD data
        """
        self.aliasName = aliasName

    def __call__( self, device, component=None, extra=None ):
        """
        @param device: the device represented by this row
        @param component: the component represented by this row (if present)
        @param extra: extra context passed to the columnHandler that will
                      generate the column value
        """
        # The summary dict has the request key/values
        summary=extra['summary']

        # The aliasDatapointPairs are the datapoints that
        # have the desired values along with the aliases
        # that may have formulas for transforming them
        aliasDatapointPairs=extra['aliasDatapointPairs']

        value = None
        # determine the row context-- device or device and component
        perfObject = component or device
        deviceTemplates = perfObject.getRRDTemplates()
        for alias, datapoint in aliasDatapointPairs:
            template = datapoint.datasource().rrdTemplate()

            # Only fetch the value if the template is bound
            # to this device or component
            if template in deviceTemplates:
                value = _fetchValueWithAlias( perfObject, datapoint,
                                              alias, summary )
            # Return the first value we find
            if value is not None:
                break

        return value


class PythonColumnHandler( object ):
    """
    A column handler accepts row context (like a device, component, or extra
    information) and returns the column value.  This class specifically
    executes a python expression that can use the row context.

    The row context includes the device object ('device') and, if available,
    the component object ('component').  It also includes report information
    such as the start date ('start') and end date ('end') of the report.
    """
    def __init__(self, talesExpression):
        """
        @param talesExpression: A python expression that can use the context
        """
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

        This is meant to be overridden.
        """
        raise Exception( 'Unimplemented: Only subclasses of AliasPlugin' +
                         ' should be instantiated directly' )

    def getCompositeColumns(self):
        """
        Return columns that will be evaluated in order and have access to
        the previous column values.  TalesColumnHandlers will have the previous
        column values for this row in their context.

        For example, if one column named 'cpuIdle' evaluates to .36,
        a composite column named 'cpuUtilized' can be created with
        a TalesColumnHandler with the expression '1 - cpuIdle'.

        NOTE: These cannot be RRD columns (or rather, RRD columns will fail
              because no datapoints will be passed to them)

        This is meant to be overridden (if needed).
        """
        return []

    def getComponentPath(self):
        """
        If the rows in the report represent components, this is how to
        get from a device to the appropriate components.

        This is meant to be overridden for component reports.
        """
        return None


    def _createRecord(self, device, component=None,
                      columnDatapointsMap={}, summary={} ):
        """
        Creates a record for the given row context
        (that is, the device and/or component)

        @param device: the device for this row
        @param component: the (optional) component for this row
        @param columnDatapointsMap: a dict of Column objects to
                                    alias-datapoint pairs.  The first
                                    datapoint that gives a value for
                                    the context will be used.
        @param summary: a dict of report parameters like start date,
                        end date, and rrd summary function
        @rtype L{Utils.Record}
        """
        def localGetValue( device, component, extra ):
            try:
                val=column.getValue( device, component,
                                     extra=extra )
            except TypeError:
                val=None
            except NameError:
                val=None
            return val

        columnValueMap = {}
        for column, aliasDatapointPairs in columnDatapointsMap.iteritems():
            columnName = column.getColumnName()
            extra=dict( aliasDatapointPairs=aliasDatapointPairs,
                        summary=summary )
            value = localGetValue( device, component, extra )
            columnValueMap[columnName] = value

        # The composite columns cannot be RRD columns, because we do
        # not pass datapoints.
        extra=dict( summary=summary )
        extra.update( columnValueMap )
        for column in self.getCompositeColumns():
            columnName = column.getColumnName()
            value = localGetValue( device, component, extra )
            columnValueMap[columnName]=value
            extra.update( { columnName : value } )

        return Utils.Record(device=device, component=component,
                            **columnValueMap)

    def _mapColumnsToDatapoints( self, dmd ):
        """
        Create a map of columns->alias/datapoint pairs.  For each
        column we need both the datapoint/alias-- the datapoint to
        retrieve the rrd data and the alias to execute the alias
        formula to transform that data (to get the correct units).

        Non-perf columns will be mapped to None
        """
        def getAliasName( column ):
            return column.getAliasName()

        # First, split the columns into perf and non-perf columns
        columns = self.getColumns()
        nonAliasColumns = filter( lambda x: getAliasName( x ) is None,
                                  columns )
        aliasColumns = filter( lambda x: getAliasName( x ) is not None,
                               columns )

        # Second, map the alias names to their columns
        aliasColumnMap = dict( zip( map( getAliasName, aliasColumns ),
                                    aliasColumns ) )

        columnDatapointsMap = {}

        # Third, map the non-perf columns to None
        for column in nonAliasColumns:
            columnDatapointsMap[column] = None

        # Fourth, match up the columns with the corresponding alias/datapoint
        # pairs
        aliasDatapointPairs = getDataPointsByAliases( dmd,
                                                      aliasColumnMap.keys() )
        for alias, datapoint in aliasDatapointPairs:
            if alias:
                column = aliasColumnMap[ alias.id ]
            else:
                # If the alias-datapoint pair is missing
                # the alias, then the column's aliasName
                # was really the datapoint name
                column = aliasColumnMap[ datapoint.id ]

            if not columnDatapointsMap.has_key( column ):
                columnDatapointsMap[column]=[]
            columnDatapointsMap[column].append( (alias,datapoint) )

        return columnDatapointsMap

    def run(self, dmd, args):
        """
        Generate the report using the columns and aliases

        @param dmd the dmd context to access the context objects
        @param args the report args from the ui

        @rtype a list of L{Utils.Record}s
        """
        # Get the summary arguments from the request args
        summary = Utilization.getSummaryArgs(dmd, args)

        # Create a dict of column to the datapoint/alias pairs
        # that return a value for the column
        columnDatapointsMap = self._mapColumnsToDatapoints( dmd )

        report = []
        componentPath = self.getComponentPath()

        # Filter the device list down according to the
        # values from the filter widget
        for device in Utilization.filteredDevices(dmd, args):
            if componentPath is None:

                record = self._createRecord( device, None,
                                             columnDatapointsMap, summary )
                report.append(record)

            else:
                components = self._getComponents( device,
                                                  componentPath )
                for component in components:
                    record = self._createRecord(device, component,
                                                columnDatapointsMap, summary)
                    report.append(record)

        return report

