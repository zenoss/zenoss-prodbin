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

TEST_TEMPLATE = 'test_template'
DEFAULT_DSDP_MAP = {'ds1':['dp1', 'dp2', 'dp3'],
                    'ds2':['dp1', 'dp2'],
                    'ds3':['dp3']
                    }

def createTemplate( dmd, templateName=TEST_TEMPLATE,
                    dsDpMap=DEFAULT_DSDP_MAP ):
    dmd.Devices.manage_addRRDTemplate( templateName )
    template = dmd.Devices.rrdTemplates._getOb( templateName )
    dsOption = template.getDataSourceOptions()[0][1]
    for dsName, datapoints in dsDpMap.iteritems():
        datasource = template.manage_addRRDDataSource( dsName, dsOption )
        for dpName in datapoints:
            datasource.manage_addRRDDataPoint( dpName )
    return template

def removeTemplate(dmd, templateName=TEST_TEMPLATE):
    dmd.Devices.manage_deleteRRDTemplates( ( templateName, ) )

def addAliases( template, aliasMap ):
    for key, value in aliasMap.iteritems():
        aliasName, formula = key
        dsName, dpName = value
        addAlias( template, dsName, dpName, aliasName, formula )
    

def addAlias( template, dsName, dpName, aliasName, aliasFormula=None):
    dp = template.datasources._getOb( dsName ).datapoints._getOb( dpName )
    dp.addAlias( aliasName, aliasFormula )

def assertAliasDatapointInMap( test, alias, datapoint, aliasDpMap):        
    aliasPair = ( alias.id, alias.formula )
    test.assert_( aliasDpMap.has_key( aliasPair ) )
    dsDpPair = ( datapoint.datasource().id, datapoint.id )
    test.assert_( aliasDpMap[ aliasPair ] == dsDpPair )
