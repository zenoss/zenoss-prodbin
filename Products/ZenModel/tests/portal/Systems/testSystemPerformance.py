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

__version__ = "$Revision: 1.1 $"[11:-2]

import unittest
import Zope
from Testing import makerequest

class GatewayPerformanceTest(unittest.TestCase):
    '''test gateway's performance screen'''
    system = (makerequest.makerequest(Zope.app())).dmd.Systems.Confmon.subsystems._getOb('Gateway').performance_view

    def testIsGateway(self):
        '''look to make sure this is gateway'''
        self.assertEqual(
            self.system().find('Gateway') != -1, 1)

    def testHasEdahl(self):
        '''look for edahl04'''
        self.assertEqual(
            self.system().find('edahl04.confmon.loc') != -1, 1)

    def testHasRouter(self):
        '''look for router'''
        self.assertEqual(
            self.system().find('router.confmon.loc') != -1, 1)

    def test5MinLoadAvg(self):
        '''look for 5 min load avg'''
        self.assertEqual(
            self.system().find('5 Minute LoadAverage') != -1, 1)

    def test5MinMemUtilization(self):
        '''look for 5 min mem utilization'''
        self.assertEqual(
            self.system().find('5 Minute Memory Utilization') != -1, 1)

class ConfmonPerformanceTest(unittest.TestCase):
    '''test confmon's performance screen'''
    system = (makerequest.makerequest(Zope.app())).dmd.Systems._getOb('Confmon').performance_view

    def testNoDevices(self):
        '''confmon shouldn't have any devices'''
        self.assertEqual(
            self.system().find('No Devices') != -1, 1)

if __name__=="__main__":
    unittest.main()
