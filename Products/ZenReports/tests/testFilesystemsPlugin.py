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

from datetime import datetime
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenModel.RRDView import RRDView
from Products.ZenModel.FileSystem import manage_addFileSystem
from Products.ZenModel.tests.RRDTestUtils import *
from Products.ZenReports.AliasPlugin import *
from Products.ZenReports.plugins.filesystems import filesystems
from Products.ZenModel.tests.RRDTestUtils import *
from Products.ZenReports.tests.ReportTestUtils import * 

def createFilesystem( device, id, blockSize, totalBlocks, usedBlocks, 
                      properties={} ):
    device.os.addFileSystem( id, False )
    filesystem = device.os.filesystems._getOb( id )
    filesystem.blockSize=blockSize
    filesystem.totalBlocks=totalBlocks
    usedBytes=blockSize*usedBlocks
    filesystem.usedBlocks_usedBlocks=usedBytes
    for key, value in properties.iteritems():
        setattr( filesystem, key, value )
    return filesystem
    
def assertFileSystemRowIsCorrect(test, records, dev2, filesystem, 
                                 testBlockSize, testTotalBlocks,
                                 testUsedBlocks ):
    record = dict( zip( map( getComponentIdFromRecord, records ), records ) )[filesystem.id]
    testTotalBytes=testBlockSize*testTotalBlocks
    testUsedBytes=testUsedBlocks*testBlockSize
    testAvailableBytes=testTotalBytes-testUsedBytes
    testPercentFull=100 - 100*float(testAvailableBytes)/float(testTotalBytes)
    assertRecordIsCorrect( test, record, dict( deviceName=dev2.id,
                                        mount=filesystem.mount,
                                        usedBytes=testUsedBytes,
                                        totalBytes=testTotalBytes,
                                        availableBytes=testAvailableBytes,
                                        percentFull=testPercentFull
                                        ) )

FILESYSTEM_TEMPLATE_ID = 'FileSystem' 

def createFileSystemTemplate( dmd ):
        template=createTemplate(dmd, FILESYSTEM_TEMPLATE_ID,
                                {'ds1':['usedBlocks_usedBlocks',]} )
        addAlias( template, 'ds1', 'usedBlocks_usedBlocks', 
                  'usedFilesystemSpace__bytes' )
        return template

def createTestDeviceWithFileSystemTemplateBound( dmd, deviceId ):
    device = createTestDevice( dmd, deviceId, {'zDeviceTemplates':
                                               [FILESYSTEM_TEMPLATE_ID,]})
    return device

class TestFilesystemsPlugin(BaseTestCase):
        
    def setUp(self):
        BaseTestCase.setUp(self)

    @replaceGetRRDValue( attributeAsRRDValue )
    def testNoValues(self):
        template=createTemplate(self.dmd, 'TestTemplate1')
        dev=createTestDevice( self.dmd, 'TestDevice1', dict(
                                zDeviceTemplates=[template.id] ) )

        records=filesystems().run( self.dmd, {} )
        self.assertEquals( 0, len( records ) )
        
    @replaceGetRRDValue( attributeAsRRDValue )
    def testOneValue(self):
        testBlockSize=10
        testTotalBlocks=20
        testUsedBlocks=5
        createFileSystemTemplate( self.dmd )      
        dev2=createTestDeviceWithFileSystemTemplateBound( self.dmd, 
                                                          'TestDevice2' )
        filesystem1=createFilesystem( dev2, 'TestFilesystem2', testBlockSize,
                                      testTotalBlocks, testUsedBlocks )
    
        plugin = filesystems()
        records = plugin.run( self.dmd, {} )
        
        self.assertEquals( 1, len( records ) )
        assertFileSystemRowIsCorrect( self, records, dev2, filesystem1, 
                                      testBlockSize, testTotalBlocks,
                                      testUsedBlocks )
        

    @replaceGetRRDValue( attributeAsRRDValue )
    def testMultipleValues(self):
        #import pydevd;pydevd.settrace()
        testProperties = [
                          ( 'testdevice3', [ ('testfs3_1', 10, 20, 15 ),
                                             ('testfs3_2', 8, 100, 98 )] ),
                          ( 'testdevice4', [ ( 'testfs4_1', 10, 20, 15 ) ] ),
                          ( 'testdevice5', [ ( 'testfs5_1', 10, 20, 15 ),
                                             ( 'testfs5_2', 10, 20, 15 ),
                                             ( 'testfs5_3', 10, 20, 15 ) ] ),
                          ( 'testdevice6', [] )
                        ]         
        createFileSystemTemplate( self.dmd )
        filesystemCount = 0
        testObjects = {}
        for propertySet in testProperties:
            device = createTestDeviceWithFileSystemTemplateBound( self.dmd,
                                                                  propertySet[0] )
            testFilesystems = []
            for filesystemProperties in propertySet[1]:
                filesystem = createFilesystem( device,
                                               filesystemProperties[0],
                                               filesystemProperties[1],
                                               filesystemProperties[2],
                                               filesystemProperties[3]                                               
                                               )
                testFilesystems.append( filesystem )
                filesystemCount += 1
            testObjects[device]=testFilesystems
        
        plugin = filesystems()
        records = plugin.run( self.dmd, {} )
        
        self.assertEquals( filesystemCount, len( records ) )
        for device, filesystemObjects in testObjects.iteritems():
            for filesystem in filesystemObjects:
                assertFileSystemRowIsCorrect( self, records, device, filesystem,
                    filesystem.blockSize,
                    filesystem.totalBlocks,
                    filesystem.usedBlocks_usedBlocks / filesystem.blockSize )

#
#    def getCompositeColumns(self):
#        return [ Column( 'availableBytes', TalesColumnHandler('totalBytes - usedBytes') ),
#                 Column( 'percentFull', TalesColumnHandler( '100 * float(availableBytes) / float(totalBytes)' ) ) ]
#    
#        records=test1.run( self.dmd, {} )
#        self.assertEquals( 1, len( records ) )
#        record=records[0]
#        self.assertEquals( dev.id, record.values['device'] )
#        self.assertEquals( dev.id, record.values['testCol1'] )
#        self.assertEquals( rackSlot, record.values['testCol3'] )
#
#        record2=recordMap[dev2.id]
#        self.assertEquals( testValue1, record2.values['testCol2'] )
#        self.assertEquals( testValue2, record2.values['testCol4'] )
#        record3=recordMap[dev3.id]
#        self.assertEquals( None, record3.values['testCol2'])
#        self.assertEquals( None, record3.values['testCol4'])
#        
#    @replaceGetRRDValue( attributeAsRRDValue )
#    def testComponentReport(self):
#        rackSlot=88
#        interfaceType='testinterfacetype'
#        template=createTemplate(self.dmd, interfaceType)
#        addAlias( template, 'ds1', 'dp1', 'testAlias1' )
#        addAlias( template, 'ds1', 'dp2', 'testAlias2' )
#        
#        dev4=createTestDevice( self.dmd, 'TestDevice2', dict(
#                                zDeviceTemplates=[template.id],
#                               rackSlot=rackSlot ) )
#        dev4.os.addIpInterface( 'testComponent1', False )
#        testComponent1=dev4.os.interfaces._getOb( 'testComponent1' )
#        testComponent1.type=interfaceType
#        
#        dev5=createTestDevice( self.dmd, 'TestDevice3', 
#                              dict( rackSlot=rackSlot ) )
#        dev5.os.addIpInterface( 'testComponent2', False )
#        testComponent2=dev5.os.interfaces._getOb( 'testComponent2' )
#        testComponent2.type='wronginterfacetype'
#
#        test3 = _TestPlugin(
#                            [
#                             Column('testCol1', 
#                                    TalesColumnHandler('component.id') ),
#                             Column('testCol3', 
#                                    TalesColumnHandler('device.rackSlot') ),
#                             RRDColumn('testCol2', 'testAlias1'),
#                             RRDColumn('testCol4', 'testAlias2')
#                            ],
#                            componentPath='os/interfaces'
#                            )
#        
#        testValue1=55
#        testValue2=77
#        testComponent1.dp1=testValue1
#        testComponent1.dp2=testValue2
#        
#        records=test3.run( self.dmd, {} )
#        self.assertEquals( 2, len( records ) )
#        recordMap=dict( zip( map( _getComponentIdFromRecord, records ), records ) )
#        for component in [testComponent1,testComponent2]:
#            record=recordMap[component.id]
#            self.assertEquals( component.device(), record.values['device'])
#            self.assertEquals( component, record.values['component'] )
#            self.assertEquals( component.id, record.values['testCol1'] )
#            self.assertEquals( rackSlot, record.values['testCol3'] )
#
#        record1=recordMap[testComponent1.id]
#        self.assertEquals( testValue1, record1.values['testCol2'] )
#        self.assertEquals( testValue2, record1.values['testCol4'] )
#        record2=recordMap[testComponent2.id]
#        self.assertEquals( None, record2.values['testCol2'])
#        self.assertEquals( None, record2.values['testCol4'])
#        
#
#    @replaceGetRRDValue( attributeAsRRDValue )
#    def testCompositeColumns(self):
#        #import pydevd;pydevd.settrace()
#        rackSlot=44
#        template=createTemplate(self.dmd, 'TestTemplate3')
#        addAlias( template, 'ds1', 'dp1', 'testAlias5' )
#        addAlias( template, 'ds1', 'dp2', 'testAlias6' )
#        dev5=createTestDevice( self.dmd, 'TestDevice5', dict(
#                                zDeviceTemplates=[template.id],
#                               rackSlot=rackSlot ) )
#        dev6=createTestDevice( self.dmd, 'TestDevice6', 
#                              dict( rackSlot=rackSlot ) )
#        test3 = _TestPlugin(
#                            [
#                             Column('testCol1', 
#                                    TalesColumnHandler('device.id') ),
#                             Column('testCol3', 
#                                    TalesColumnHandler('device.rackSlot') ),
#                             RRDColumn('testCol2', 'testAlias5'),
#                             RRDColumn('testCol4', 'testAlias6')
#                            ],
#                            [
#                             Column('testCol5',TalesColumnHandler('testCol2 and testCol4 and ( testCol2 + testCol4 ) / 10'))
#                            ]
#                            )
#        
#        testValue1=120
#        testValue2=240
#        dev5.dp1=testValue1
#        dev5.dp2=testValue2
#        
#        records=test3.run( self.dmd, {} )
#        self.assertEquals( 2, len( records ) )
#        recordMap=dict( zip( map( _getDeviceIdFromRecord, records ), records ) )
#        for dev in [dev5,dev6]:
#            record=recordMap[dev.id]
#            self.assertEquals( dev, record.values['device'] )
#            self.assertEquals( dev.id, record.values['testCol1'] )
#            self.assertEquals( rackSlot, record.values['testCol3'] )
#
#        record5=recordMap[dev5.id]
#        self.assertEquals( testValue1, record5.values['testCol2'] )
#        self.assertEquals( testValue2, record5.values['testCol4'] )
#        self.assertEquals( ( testValue1 + testValue2 ) / 10, 
#                             record5.values['testCol5'] )
#        record6=recordMap[dev6.id]
#        self.assertEquals( None, record6.values['testCol2'])
#        self.assertEquals( None, record6.values['testCol4'])
#        self.assert_( 'testCol6' not in record6.values.keys() )



def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestFilesystemsPlugin))
    return suite

