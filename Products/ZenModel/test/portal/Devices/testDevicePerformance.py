#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__version__ = "$Revision: 1.1 $"[11:-2]

import unittest
import Zope
from Testing import makerequest

class Edahl04PerformanceTest(unittest.TestCase):
    '''test device performance screen'''
    dev = (makerequest.makerequest(Zope.app())).dmd.Devices.Servers.Linux._getOb('edahl04.confmon.loc').viewPerformance

    def testHas5MinLoadAvg(self):
        '''make sure edahl04 has 5 minute load average'''
        self.assertEqual(
            self.dev().find('5 Minute LoadAverage') != -1, 1)

    def testHasTotalCPU(self):
        '''make sure edahl04 is collecting total cpu'''
        self.assertEqual(
            self.dev().find('Total CPU') != -1, 1)

    def testHasRealMemory(self):
        '''make sure edahl04 is collecting real mem'''
        self.assertEqual(
            self.dev().find('Real Memory') != -1, 1)

    def testHasSwapMemory(self):
        '''make sure edahl04 is collecting swap mem'''
        self.assertEqual(
            self.dev().find('Swap Memory') != -1, 1)

class RouterPerformanceTest(unittest.TestCase):
    '''test device performance screen'''
    dev = (makerequest.makerequest(Zope.app())).dmd.Devices.NetworkDevices.Router._getOb('router.confmon.loc').viewPerformance

    def testHas5MinLoadAvg(self):
        '''make sure router has 5 minute memory'''
        self.assertEqual(
            self.dev().find('5 Minute Memory Utilization') != -1, 1)

    def testHasTotalCPU(self):
        '''make sure router is collecting cpu'''
        self.assertEqual(
            self.dev().find('CPU Utilization') != -1, 1)

if __name__=="__main__":
    unittest.main()
