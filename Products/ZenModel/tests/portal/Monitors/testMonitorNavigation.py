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

class ListMonitorTest(unittest.TestCase):
    '''test to see if we can navigate and investigate monitors'''
    monitors = (makerequest.makerequest(Zope.app())).dmd.Monitors.index_html
    
    def testFindCricket(self):
        '''make sure cricket is in the monitors directory'''
        self.assertEqual(
            self.monitors().find('"/dmd/Monitors/Cricket"') != -1, 1)

    def testFindPingMonitors(self):
        '''make sure pingmonitors is in the monitors directory'''
        self.assertEqual(
            self.monitors().find('"/dmd/Monitors/PingMonitors"') != -1, 1)

class CricketListTest(unittest.TestCase):
    '''make sure edahl04 is in the cricket directory'''
    monitors = (makerequest.makerequest(Zope.app())).dmd.Monitors.Cricket.index_html

    def testHasEdahl04(self):
        '''make sure there is an edahl04 cricket server'''
        self.assertEqual(
            self.monitors().find('"/dmd/Monitors/Cricket/edahl04.confmon.loc"') != -1, 1)

class PingMonitorListTest(unittest.TestCase):
    '''make sure there is a default ping monitor'''
    monitors = (makerequest.makerequest(Zope.app())).dmd.Monitors.PingMonitors.index_html

    def testHasDefault(self):
        '''make sure the default exists'''
        self.assertEqual(
            self.monitors().find('"/dmd/Monitors/PingMonitors/Default"') != -1, 1)

if __name__ == "__main__":
    unittest.main()
