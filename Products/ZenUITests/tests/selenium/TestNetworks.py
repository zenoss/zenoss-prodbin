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
# the "Networks" Browse By subheading.
#
# Noel Brockett
#

import unittest

from SelTestBase import SelTestBase

class TestNetworks(SelTestBase):
    """Defines a class that runs tests under the Networks heading"""

    def testAddNetwork(self):
        """Run tests on the Networks page"""
        
        self.waitForElement("link=Networks")
        self.selenium.click("link=Networks")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.addDialog("SubnetworksaddNetwork",new_id=("text", "10.1.10.1"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog("SubnetworksdeleteNetwork", form_name="subnetworkForm", testData="10.1.10.1")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        
if __name__ == "__main__":
    unittest.main()
