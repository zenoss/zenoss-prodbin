###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import re

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenRRD.zenprocess import ZenProcessTask
from Products.ZenUtils.Utils import zenPath
from Products.ZenHub.services.ProcessConfig import ProcessProxy


class Options(object): pass

class Preferences(object):
    options = Options()

class EventService(object):
    def sendEvent(self, *args, **kwargs):
        pass

class TaskConfig(object):
    name = 'devicename'
    manageIp = '192.168.10.10'
    zMaxOIDPerRequest = 1
    lastmodeltime = 'datestring'
    snmpConnInfo = {}
    _preferences = object()
    _eventService = object()
    thresholds = []
    processes = {}

    def __init__(self, procDefs=None):
        if procDefs is not None:
            self.processes = procDefs


class TestZenprocess(BaseTestCase):

    def getFileData(self, filename):
        base = zenPath('Products/ZenRRD/tests/zenprocess_data')
        data = None
        name = base + '/' + filename
        try:
            dataAsString = open(name).read()
            data = eval(dataAsString)
            self.assert_(data is not None,
                         "No data from file %s" % filename)
        except Exception, ex:
            log.warn('Unable to evaluate data file %s because %s',
                     name, str(ex))
        return data

    def makeTask(self, procDefs):
        config = TaskConfig(procDefs=procDefs)
        task = ZenProcessTask('bogodevice', 'taskname', 0, config)
        task._preferences = Preferences()
        task._preferences.options.showrawtables = False
        task._preferences.options.showprocs = False
        task._preferences.options.captureFilePrefix = ''
        task._eventService = EventService()
        return task

    def compareTestFile(self, filename, task, expectedStats):
        """
        The expectedStats is a tuple containing numbers for the
        following:

        procs, afterByConfig, afterPidToProcessStats, beforeByConfig, newPids, restarted

        The results are passed back from the method
        """
        data = self.getFileData(filename)

        # Split out the expected stats
        (eprocs, eafterByConfig, eafterPidToProcessStats,
                ebeforeByConfig, enewPids, erestarted, edeadPids) = expectedStats

        procs = task._parseProcessNames(data)
        self.assert_(len(procs) == eprocs,
                     "%s contained %d processes, expected %d" %(
                       filename, len(procs), eprocs))

        results = task._determineProcessStatus(procs)
        (afterByConfig, afterPidToProcessStats,
                beforeByConfig, newPids, restarted, deadPids) = results

        self.assert_(len(newPids) == enewPids,
                     "%s: Expected %d new processes, got %d" % (
                       filename, enewPids, len(newPids)))
        self.assert_(len(restarted) == erestarted,
                     "%s: Expected %d restarted processes, got %d" % (
                       filename, erestarted, len(restarted)))

        # Save the results of the run
        task._deviceStats._pidToProcess = afterPidToProcessStats

        # Return back the results in case somebody wants to dive in
        return procs, results

    def updateProcDefs(self, procDefs, name, ignoreParams, regex):
        procDef = ProcessProxy()
        procDef.name = name
        procDef.regex = re.compile(regex)
        procDef.ignoreParameters = ignoreParams
        procDefs[procDef.name] = procDef

    def testMingetty(self):
        """
        Sanity check for simplified example
        """
        procDefs = {}
        self.updateProcDefs(procDefs, 'mingetty', True, '/sbin/mingetty')
        mingetty = procDefs['mingetty']
        task = self.makeTask(procDefs)

        expectedStats = (6, 0, 0, 0, 6, 0, 0)
        self.compareTestFile('mingetty-0', task, expectedStats)

        # No changes if there are no changes
        expectedStats = (6, 0, 0, 0, 0, 0, 0)
        self.compareTestFile('mingetty-0', task, expectedStats)

        # Note: the restart count is only used if we want to
        #       receive notifications
        expectedStats = (6, 0, 0, 0, 1, 0, 0)
        self.compareTestFile('mingetty-1', task, expectedStats)

        mingetty.restart = True
        expectedStats = (6, 0, 0, 0, 1, 1, 0)
        self.compareTestFile('mingetty-0', task, expectedStats)

        # Now treat the processes independently
        mingetty.ignoreParameters = False
        expectedStats = (6, 0, 0, 0, 1, 1, 0)
        self.compareTestFile('mingetty-1', task, expectedStats)

    def testCase15875part1(self):
        procDefs = {}
        self.updateProcDefs(procDefs, 'syslogd', False, '^syslogd')
        self.updateProcDefs(procDefs, 'usr_bin_perl', False, '^.*?/usr/bin/perl\s+-w\s+/opt/sysadmin/packages/scooper/bin/scooperd\s+/opt.*')
        self.updateProcDefs(procDefs, 'usr_java_jdk_bin_java', False, '/opt/gsp/')
        self.updateProcDefs(procDefs, 'ntpd', False, '^ntpd')
        self.updateProcDefs(procDefs, 'ntpd', False, '^ntpd')
        self.updateProcDefs(procDefs, 'perl', False, 'aSecure\.rb|aSecure\.pl')
        self.updateProcDefs(procDefs, 'crond', True, '^crond')

        task = self.makeTask(procDefs)
        expectedStats = (117, 0, 0, 0, 7, 0, 0)
        procs, results = self.compareTestFile('case15875-0', task, expectedStats)

    def testCase15875part2(self):
        """
        Test the case where we want to know about the arg lists.  This adds the
        MD5 hash into the name of the process definition.
        """
        procDefs = {}
        self.updateProcDefs(procDefs, 'usr_java_jdk1.6_bin_java a9286b43deac884c793529289e7b1a61', False, '.*?/opt/tomcat-emailservice-')
        self.updateProcDefs(procDefs, 'usr_java_jdk1.6_bin_java 46213332b61b77a47dafd204cb7ea2db', False, '.*?/opt/tomcat-emailservice-')
        self.updateProcDefs(procDefs, 'usr_java_jdk1.6_bin_java 6180cffd001309eeec52efdb5f4ae007', False, '.*?/opt/tomcat-emailservice-')

        task = self.makeTask(procDefs)
        expectedStats = (97, 0, 0, 0, 3, 0, 0)
        procs, results = self.compareTestFile('case15875-1', task, expectedStats)

        # Now what happens when the remote agent screws up a bit
        # and *ALMOST* sends us all the stuff?
        expectedStats = (97, 0, 0, 0, 0, 0, 0)
        procs, results = self.compareTestFile('case15875-2', task, expectedStats)
        deadPids = results[-1]
        
        self.assert_(len(deadPids) == 0,
                     "Failed to recover from terrible SNMP agent output")

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestZenprocess))
    return suite

