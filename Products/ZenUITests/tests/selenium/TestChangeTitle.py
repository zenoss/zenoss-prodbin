#!/usr/bin/python
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

import unittest

from SelTestBase import SelTestBase,TARGET,DEFAULT_DEVICE_CLASS

class TestChangeTitle(SelTestBase):
    """Base class for performing tests on specific device instances"""

    prefix = 'sel-test'

    def setUp(self):
        """Customized setUp for device instance tests"""
        SelTestBase.setUp(self)

        self.dev1Id = self.prefix + 'aaaa'
        self.dev1Title = self.prefix + 'cccc'
        self.dev2Id = self.prefix + 'bbbb'

        #make sure old tests were cleaned up
        self.deleteThisTestsDevices()

        self.addDevice( self.dev1Id )
        self.addDevice( self.dev2Id )
        self.editDevice( self.dev1Id, title=self.dev1Title)

    def tearDown(self):
        """Customized tearDown for device instance tests"""
        self.deleteThisTestsDevices()
        SelTestBase.tearDown(self)

    def deleteThisTestsDevices( self ):
        self.deleteDevice(self.dev1Id, expectedToBePresent=False)
        self.deleteDevice(self.dev2Id, expectedToBePresent=False)

    def testDeviceNameIsTitleAndBreadCrumbs(self):
        self.goToDevice(self.dev1Id)
        self.waitForElement( 'link=%s' % self.dev1Title, self.WAITTIME )
        self.assert_( ( 'Device: %s' % self.dev1Title ) in
                      self.selenium.get_body_text() )
        self.assertEqual( self.selenium.get_title(), 'Zenoss: %s' % self.dev1Title )

    def testDeviceListHasTitle(self):
        self.selenium.click("link=Device List")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.waitForElement("filter")
        self.selenium.focus("filter")
        self.type_keys( "filter", self.prefix )
        self.waitForElement( 'link=%s' % self.dev2Id )
        bodytext = self.selenium.get_body_text()
        dev1location = bodytext.find( self.dev1Title )
        dev2location = bodytext.find( self.dev2Id )
        self.assert_( dev1location >= 0 )
        self.assert_( dev2location >= 0 )
        # Now make sure sort is correct
        self.assert_( dev2location < dev1location )

    def testDeleteFromDeviceListByTitle(self):
        self.selenium.click("link=Device List")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.waitForElement("filter")
        self.selenium.focus("filter")
        self.type_keys( "filter", self.prefix )
        self.waitForElement( 'link=%s' % self.dev1Title )
        self.selenium.click( self.dev1Id )
        self.addDialog( "javascript:$('dialog').show($('DeviceGridlistremoveDevicesgridinput').form, '/zport/dmd/Devices/dialog_removeDevices_grid')",
                        "removeDevices:method", waitForSubmit=False )
        self.waitForElement("//div[contains(@id,'smoke-notification')]")
        self.selenium.click("link=Device List")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.waitForElement("filter")
        self.selenium.focus("filter")
        self.type_keys( "filter", self.prefix )
        self.waitForElement( 'link=%s' % self.dev2Id )
        bodytext = self.selenium.get_body_text()
        self.assert_( self.dev1Title not in bodytext )

    def testDeviceClassDeviceListHasTitle(self):
        self.selenium.open( '/zport/dmd/Devices/%s' % DEFAULT_DEVICE_CLASS )
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click( 'showAll' )
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        bodytext = self.selenium.get_body_text()
        dev1location = bodytext.find( self.dev1Title )
        dev2location = bodytext.find( self.dev2Id )
        self.assert_(dev1location >= 0)
        self.assert_(dev2location >= 0)
        self.assert_(dev2location < dev1location)


    def testEventDeviceLinkWorksWithTitle(self):
        self.selenium.open( '/zport/dmd/Events' )
        self.waitForElement('xpath=//a[contains(@href,"/zport/dmd/Events/viewEvents")]', self.WAITTIME)
        self.selenium.click('xpath=//a[contains(@href,"/zport/dmd/Events/viewEvents")]')
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.addDialog( addType="javascript:$('dialog').show(this.event, '/zport/dmd/Events/dialog_addEvent')",
                        addMethod='manage_addEvent:method',
                        message=('text', 'test message'),
                        device=('text', self.dev1Title ),
                        severity=('select', 'Critical') )
        #just added as critical, should be first.  Note:  This isn't the
        #real test... We need one where the device field on the event
        #is the title
        self.waitForElement('link=%s' % self.dev1Id, self.WAITTIME)

##UGH TOO MUCH JAVASCRIPT
##    def testPortletsShowTitle(self):
#        #ObjectWatchList first
#        #ProductionStates
#        #DeviceIssues

    def testDeviceReportShowsTitle(self):
        self.selenium.click("link=Reports")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("link=Device Reports")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("link=All Devices")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click( 'showAll' )
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.waitForElement( 'link=%s' % self.dev1Title )
        self.selenium.click( 'link=%s' % self.dev1Title )
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.assertEqual( self.selenium.get_title(), 'Zenoss: %s' % self.dev1Title )

if __name__ == "__main__":
    unittest.main()
