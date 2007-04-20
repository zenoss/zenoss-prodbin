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

class Edahl04ChangesTest(unittest.TestCase):
    '''check edahl04 for the initial load entry'''
    dev = (makerequest.makerequest(Zope.app())).dmd.Devices.Servers.Linux._getOb('edahl04.confmon.loc').viewHistory

    def testFindInitialLoad(self):
        '''look for the initial load'''
        self.assertEqual(
            self.dev().find('Initial load') != -1, 1)

class RouterChangeTest(unittest.TestCase):
    '''check router for the initial load entry'''
    dev = (makerequest.makerequest(Zope.app())).dmd.Devices.NetworkDevices.Router._getOb('router.confmon.loc').viewHistory

    def testFindInitialLoad(self):
        '''look for the initial load'''
        self.assertEqual(
            self.dev().find('Initial load') != -1, 1)

if __name__=="__main__":
    unittest.main()
