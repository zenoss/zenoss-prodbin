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

import unittest
from twisted.conch.error import ConchError
from Products.DataCollector import SshClient

def doNothing(*args, **kwargs):
    pass

class FakeLog(object):
    def warn(self, message, *args):
        self.message = message % args

class OpenFailedTestCase(unittest.TestCase):
    """Tests regression of ticket #1483"""

    def setUp(self):
        self.log = SshClient.log
        SshClient.log = FakeLog()
        self.sendEvent = SshClient.sendEvent
        SshClient.sendEvent = doNothing

    def runTest(self):
        channel = SshClient.CommandChannel('foo')
        #channel.command = 'foo'
        channel.openFailed(ConchError('quux', 22))
        self.assertEqual('None CommandChannel Open of foo failed (error code 22): quux',
                         SshClient.log.message)

    def tearDown(self):
        SshClient.log = self.log
        SshClient.sendEvent = self.sendEvent

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(OpenFailedTestCase))
    return suite
