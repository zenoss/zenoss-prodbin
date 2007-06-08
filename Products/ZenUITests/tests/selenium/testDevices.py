#!/usr/bin/python
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

#
# Contained below is the class that tests elements located under
# the "Devices" class heading.
#
# Adam Modlin and Nate Avers
#

import unittest

from selTestBase import selTestBase

class DevicesTest(selTestBase):
    """
    Defines an object that runs tests against a Device Class.
    """
    
    def testDeviceClass(self):
        """
        Run tests on the Devices page
        """
        self.waitForElement("link=Devices")
        self.selenium.click("link=Devices")
        self.waitForElement("link=Templates")
        self.selenium.click("link=Templates")
        self.addDialog(addType="TemplatesaddTemplate")
        self.deleteDialog(deleteType="TemplatesdeleteTemplates", deleteMethod="manage_deleteRRDTemplates:method",
                            pathsList="ids:list", form_name="templates")
        
if __name__ == "__main__":
    unittest.main()