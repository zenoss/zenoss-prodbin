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

import logging
log = logging.getLogger('zen.testzenprocess')

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

        # Blow away any cached config data
        if 'devicename' in task.DEVICE_STATS:
            del ZenProcessTask.DEVICE_STATS['devicename']

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

    def testCase15875part3(self):
        procDefs = {}

        self.updateProcDefs(procDefs, 'opt_zenoss_bin_python 989031ccce92ac84e183a6f127b3e279', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)
        self.updateProcDefs(procDefs, 'java b2bdc8a61846f09f58aec8c748a204e4', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)
        self.updateProcDefs(procDefs, 'opt_zenoss_bin_python adb8994c7ba8b1f6395cc8dc12ba5c1b', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)
        self.updateProcDefs(procDefs, 'opt_zenoss_bin_python 286221f4ce20c06cb4777df35ec5ed89', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)
        self.updateProcDefs(procDefs, 'opt_zenoss_bin_python 4775a3fa1682df2f095aab454031d702', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)
        self.updateProcDefs(procDefs, 'opt_zenoss_bin_python fba04951fda76b915671af901bb874b5', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)
        self.updateProcDefs(procDefs, 'opt_zenoss_bin_python dcac4d78470d919d41a24f0fa32dda90', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)
        self.updateProcDefs(procDefs, 'ntpd 869db238ffc5f88024ff5fb8ffabb084', False, '^ntpd',)
        self.updateProcDefs(procDefs, 'java bbffd7e3fa9d6853d7682156d5dd7e97', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)
        self.updateProcDefs(procDefs, 'usr_sbin_httpd', True, '^[^ ]*httpd[^ /]*( |$)',)
        self.updateProcDefs(procDefs, 'opt_zenoss_bin_python 1b480820ba996e468d89297c15b842e9', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)
        self.updateProcDefs(procDefs, 'opt_zenoss_bin_python f686cbe618bf158a01ce23f10573518d', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)
        self.updateProcDefs(procDefs, 'opt_zenoss_bin_python 799802c1cb9d56c0b7a036f59512176e', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)
        self.updateProcDefs(procDefs, 'opt_zenoss_bin_python 4d2eeb2773decebf5bf03c657d6a66c9', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)
        self.updateProcDefs(procDefs, 'opt_zenoss_bin_python 4fb2e41e1057bc98418ea3923ff924d0', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)
        self.updateProcDefs(procDefs, 'opt_zenoss_bin_python b1decc46fd0d2006952e773ab2fb3ae2', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)
        self.updateProcDefs(procDefs, 'opt_zenoss_bin_python f2eaff8e78abf5423d41b9698137e28d', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)
        self.updateProcDefs(procDefs, 'opt_zenoss_bin_python e83ae4187a18d82891c7f877c4036edb', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)
        self.updateProcDefs(procDefs, 'opt_zenoss_bin_python 18aeb381536e1f263037fb2c830cf293', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)
        self.updateProcDefs(procDefs, 'opt_zenoss_bin_python 560d3c6b462208bbf41807626c87ca8a', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)
        self.updateProcDefs(procDefs, 'opt_zenoss_bin_python c73166185748470cff8468fbad6f8d15', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)
        self.updateProcDefs(procDefs, 'crond', True, '^crond',)
        self.updateProcDefs(procDefs, 'opt_zenoss_bin_python ce658ba39869d9238ef281fdd7829058', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)
        self.updateProcDefs(procDefs, 'opt_zenoss_bin_python 895c56a50ec67fb7253d3c5bf16e54fc', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)
        self.updateProcDefs(procDefs, 'opt_zenoss_bin_python fbabb34cc04d9a7b1b49927c55608dce', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)
        self.updateProcDefs(procDefs, 'opt_zenoss_bin_python 0297fd22e7fd76c7996b0cec7b65edfd', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)
        self.updateProcDefs(procDefs, 'opt_zenoss_bin_python 65e57f32917b59ccb63a264a2e7fdb9c', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)
        self.updateProcDefs(procDefs, 'usr_sbin_mysqld', True, 'sbin\/mysqld',)
        self.updateProcDefs(procDefs, 'opt_zenoss_bin_python e9c6b5fc30781634e8a4c8e179ba6bee', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)
        self.updateProcDefs(procDefs, 'opt_zenoss_bin_python 43a302e41b239c0dd962bb6f5108f033', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)
        self.updateProcDefs(procDefs, 'opt_zenoss_bin_python cbeab9686cc961499879ca1abf83598e', False, '^(?!^.*zenmodeler.*?--now|^.*ZenWebTx.*?|^.*?\/tmp/tmp).*?/opt/zenoss/bin/python /opt/zenoss/|java .*?/opt/zenoss/',)

        task = self.makeTask(procDefs)
        expectedStats = (174, 0, 0, 0, 53, 0, 0)
        procs, results = self.compareTestFile('case15875-3', task, expectedStats)

    def testCase15875part4(self):
        procDefs = {}

        self.updateProcDefs(procDefs, 'usr_bin_perl', True, '^.*\/*httpd')
        self.updateProcDefs(procDefs, 'usr_sbin_slurpd', True, '/usr/sbin/(?:slapd|slurpd)')
        self.updateProcDefs(procDefs, 'ntpd b5552db5824a818094a496e52982919e', False, '^ntpd')
        self.updateProcDefs(procDefs, 'syslogd 14cc14f9b12338978b9d35cbb947581b', False, '^syslogd')
        self.updateProcDefs(procDefs, 'usr_sbin_slapd', True, '/usr/sbin/(?:slapd|slurpd)')
        self.updateProcDefs(procDefs, 'usr_sbin_httpd', True, '^[^ ]*httpd[^ /]*( |$)')
        self.updateProcDefs(procDefs, 'crond', True, '^crond')

        task = self.makeTask(procDefs)
        expectedStats = (253, 0, 0, 0, 14, 0, 0)
        procs, results = self.compareTestFile('case15875-4', task, expectedStats)

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestZenprocess))
    return suite

