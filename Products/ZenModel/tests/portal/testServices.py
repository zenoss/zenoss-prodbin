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

class ServicesListTest(unittest.TestCase):
    '''make sure the services are navigable'''
    servs = (makerequest.makerequest(Zope.app())).dmd.Services.index_html

    def testHasIpServices(self):
        '''make sure IpServices are here'''
        self.assertEqual(
            self.servs().find('/dmd/Services/IpServices') != -1, 1)

class IpServicesBlankTest(unittest.TestCase):
    '''make sure that ipservices doesn't contain anything'''
    servs = (makerequest.makerequest(Zope.app())).dmd.Services.IpServices.index_html

    def testHasNoServices(self):
        '''make sure there aren't any services'''
        self.assertEqual(
            self.servs().find('No contents') != -1, 1)

if __name__ == "__main__":
    unittest.main()
