#!/usr/bin/python
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


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
