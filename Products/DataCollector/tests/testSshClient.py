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
    def debug(self, message, *args):
        self.debugmessage = message % args
    def warn(self, message, *args):
        self.message = message % args

class FakeDevice(object):
    zCommandUsername = ''
    zCommandPassword = ''
    zCommandLoginTries = 3
    zCommandLoginTimeout = 10
    zCommandCommandTimeout = 10
    zKeyPath = ''
    zSshConcurrentSessions = 10
    zCommandPort = 22
    zCommandSearchPath = ''
    zCommandExistanceTest = ''
    id = ''

    def __init__(self, id='testDevice'):
        self.id = id

class FakeOptions(object):
    username = ''
    password = ''
    loginTries = 3
    loginTimeout = 10
    commandTimeout = 10
    keyPath = ''
    concurrentSessions = 10
    searchPath = ''
    existenceTest = ''


class OpenFailedTestCase(unittest.TestCase):
    """Tests regression of ticket #1483"""

    def setUp(self):
        self.log = SshClient.log
        SshClient.log = FakeLog()
        self.sendEvent = SshClient.sendEvent
        SshClient.sendEvent = doNothing
        self.device = FakeDevice('testDevice')
        self.options = FakeOptions()

    def testOpen(self):
        channel = SshClient.CommandChannel('foo')
        channel.openFailed(ConchError('quux', 22))
        self.assertEqual('None CommandChannel Open of foo failed (error code 22): quux',
                         SshClient.log.message)

    def _resetClient(self, name, maxJobs=100):
        self.client = SshClient.SshClient(hostname=name,
                    ip='127.0.0.1',
                    device=self.device, options=self.options)
        class ConnectionObject(object):
            def addCommand(self, cmd):
                pass

        for cmd in range(maxJobs):
            self.client.addCommand(str(cmd))

        # If we set this before adding commands, runCommands() gets called
        self.client.connection = ConnectionObject()

    def testConcurrentConnections(self):
        # Note: it seems that we currently treat concurrentSessions == 0
        #       to mean 'no SSH sessions'.  It might be better to treat
        #       it as 'unlimited SSH sessions'.
        self._resetClient('testDevice')
        self.client.concurrentSessions = 0
        self.assertEqual(len(self.client.workList), 100)
        self.client.runCommands()
        self.assertEqual(len(self.client.workList), 100)

        self._resetClient('testDevice')
        self.client.concurrentSessions = 1
        self.assertEqual(len(self.client.workList), 100)
        self.client.runCommands()
        self.assertEqual(len(self.client.workList), 99)

        self._resetClient('testDevice')
        self.client.concurrentSessions = 10
        self.assertEqual(len(self.client.workList), 100)
        self.client.runCommands()
        self.assertEqual(len(self.client.workList), 90)

        self._resetClient('testDevice')
        self.client.concurrentSessions = 100
        self.assertEqual(len(self.client.workList), 100)
        self.client.runCommands()
        self.assertEqual(len(self.client.workList), 0)

        self._resetClient('testDevice')
        self.client.concurrentSessions = 110
        self.assertEqual(len(self.client.workList), 100)
        self.client.runCommands()
        self.assertEqual(len(self.client.workList), 0)

    def tearDown(self):
        SshClient.log = self.log
        SshClient.sendEvent = self.sendEvent

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(OpenFailedTestCase))
    return suite
