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

class ConfmonChangeTest(unittest.TestCase):
    '''make sure that Confmon was built by loader.py'''
    systems = (makerequest.makerequest(Zope.app())).dmd.Systems._getOb('Confmon').viewHistory

    def testInitialLoad(self):
        '''created by loader.py?'''
        self.assertEqual(
            self.systems().find('Initial load') != -1, 1)

class GatewayChangeTest(unittest.TestCase):
    '''make sure gateway was built with loader.py'''
    systems = (makerequest.makerequest(Zope.app())).dmd.Systems.Confmon.subsystems._getOb('Gateway').viewHistory

    def testInitialLoad(self):
        '''make sure gateway way built by loader.py'''
        self.assertEqual(
            self.systems().find('Initial load') != -1, 1)

if __name__=="__main__":
    unittest.main()
