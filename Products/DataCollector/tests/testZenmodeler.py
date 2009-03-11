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

import logging
import time
import unittest

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.DataCollector.zenmodeler import ZenModeler
from Products.ZenWin.WMIClient import WMIClient

log = logging.getLogger("zen.testcases")

def doNothing(*args):
    pass
    
class FakeDevice(object):
    id = 'fakeDevice'
    manageIp = None
    zWinUser = None
    zWinPassword = None

class TimeoutClientTestCase(BaseTestCase):
    
    def runTest(self):
        # setup
        ZenModeler.__init__ = doNothing
        modeler = ZenModeler()
        modeler.log = log
        modeler.finished = []
        
        # a big part of what is tested is that the WMIClient constructor
        # creates and object that has all of the methods necessary for
        # _timeoutClients.
        client = WMIClient(FakeDevice())
        
        modeler.clients = [client]
        client.timeout = time.time() - 1
        
        # function under test
        modeler._timeoutClients()
        
        # make assertions
        self.assertEqual([client], modeler.finished)
        self.assert_(client.timedOut)
        self.failIf(modeler.clients)
        
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TimeoutClientTestCase))
    return suite
