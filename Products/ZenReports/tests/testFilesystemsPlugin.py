##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


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
        
    @replaceGetRRDValue( attributeAsRRDValue )
    def testNoValues(self):
        template=createTemplate(self.dmd, 'TestTemplate1')
        dev=createTestDevice( self.dmd, 'TestDevice1', dict(
                                zDeviceTemplates=[template.id] ) )

        records=filesystems().run( self.dmd, {'deviceClass':'/Devices/Server', 'generate':True} )
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
        records = plugin.run( self.dmd, {'deviceClass':'/Devices/Server', 'generate':True} )
        
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
        records = plugin.run( self.dmd, {'deviceClass':'/Devices/Server', 'generate':True} )
        
        self.assertEquals( filesystemCount, len( records ) )
        for device, filesystemObjects in testObjects.iteritems():
            for filesystem in filesystemObjects:
                assertFileSystemRowIsCorrect( self, records, device, filesystem,
                    filesystem.blockSize,
                    filesystem.totalBlocks,
                    filesystem.usedBlocks_usedBlocks / filesystem.blockSize )




def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestFilesystemsPlugin))
    return suite
