###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import unittest
from Products.ZenUtils.IpUtil import ensureIp


class IpUtilsTest(unittest.TestCase):
    """ Tests functions on the IpUtils module"""
    
    def testEnsureIp(self):
        ip = '10'
        self.assertEqual(ensureIp(ip), '10.0.0.0')

        # strips the characters
        ip = '10a.12.aaa'
        self.assertEqual(ensureIp(ip), '10.12.0.0')

        # invalid number
        ip = '1212121212121'
        self.assertEqual(ensureIp(ip), '0.0.0.0')
                         
def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(IpUtilsTest),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
