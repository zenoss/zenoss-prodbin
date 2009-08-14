###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import Globals
import zope.interface

from twisted.internet import base, defer, reactor
from twisted.trial import unittest

from Products.ZenCollector.daemon import CollectorDaemon
from Products.ZenCollector.interfaces import ICollectorPreferences,\
                                             IScheduledTask,\
                                             IScheduler
from Products.ZenCollector.tasks import DeviceTaskSplitter
from Products.ZenTestCase.BaseTestCase import BaseTestCase

base.DelayedCall.debug = True

class TestCollectorConfigurator(object):
    zope.interface.implements(ICollectorPreferences)

    def __init__(self):
        self.collectorName = "test"
        self.defaultRRDCreateCommand = None
        self.cycleInterval = 0 # seconds
        self.configCycleInterval = 0 # minutes
        self.configurationService = 'nota'

    def buildOptions(self, parser):
        pass

class TestTask(object):
    zope.interface.implements(IScheduledTask)

class TestCollectorDaemon(BaseTestCase):

    def testPingIssues(self):
        """
        Test ping issues handling by validating that the scheduler properly
        pauses and resumes tasks based upon the ping issues results.
        """
        pausedDevices = []
        resumedDevices = []
        testPingIssues = []

        # create a test scheduler that just keeps track of what was paused
        class PingTestScheduler(object):
            zope.interface.implements(IScheduler)

            def addTask(self, newTask):
                pass

            def removeTasksForDevice(self, devId):
                pass

            def pauseTasksForDevice(self, devId):
                pausedDevices.append(devId)

            def resumeTasksForDevice(self, devId):
                resumedDevices.append(devId)

        # create a test daemon that lets us just test ping issues
        class PingTestDaemon(CollectorDaemon):
            def __init__(self):
                super(PingTestDaemon, self).__init__(TestCollectorConfigurator, 
                                               DeviceTaskSplitter,
                                               TestTask)
                self._scheduler = PingTestScheduler()

            def getDevicePingIssues(self):
                return defer.succeed(testPingIssues)

        # create our test daemon and force the cycle option on so that the
        # maintenance cycle will take place when asked
        daemon = PingTestDaemon()
        daemon.options.cycle = True

        testPingIssues.append(('foobar.zenoss.loc', 1, 3))
        d = daemon._maintenanceCycle()

        # validate that in the first maintenance cycle that foobar.zenoss.loc
        # is paused
        def _allDone1(result):
            self.assertTrue('foobar.zenoss.loc' in pausedDevices)
            self.assertTrue('some fake device' not in pausedDevices)

            # prepare for the second test by clearing all ping issues
            del testPingIssues[:]
            return daemon._maintenanceCycle()

        # validate that foobar.zenoss.loc is now successfully resumed
        def _allDone2(result):
            self.assertTrue('foobar.zenoss.loc' in resumedDevices)
            self.assertTrue('some fake device' not in resumedDevices)

        d.addBoth(_allDone1)
        d.addBoth(_allDone2)
        return d
