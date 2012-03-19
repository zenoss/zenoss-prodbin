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
import sys
from Products.ZenModel.OSProcess import getProcessIdentifier

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

class ProcessResults(object):
    PROCESSES = 'PROCESSES'
    AFTERBYCONFIG = 'AFTERBYCONFIG'
    AFTERPIDTOPS = 'AFTERPIDTOPS'
    BEFOREBYCONFIG = 'BEFOREBYCONFIG'
    NEW = 'NEW'
    RESTARTED = 'RESTARTED'
    DEAD = 'DEAD'
    MISSING = 'MISSING'

    orderedKeys = (PROCESSES,AFTERBYCONFIG, AFTERPIDTOPS, BEFOREBYCONFIG, NEW, RESTARTED, DEAD, MISSING)
    resultKeys = (AFTERBYCONFIG, AFTERPIDTOPS, BEFOREBYCONFIG, NEW, RESTARTED, DEAD, MISSING)

class TestZenprocess(BaseTestCase):

    def getFileData(self, filename):
        base = zenPath('Products/ZenRRD/tests/zenprocess_data')
        data = None
        name = base + '/' + filename
        try:
            dataAsString = open(name).read()
            data = eval(dataAsString)
        except Exception, ex:
            log.warn('Unable to evaluate data file %s because %s', name, str(ex))

        self.assert_(data is not None, "No data from file %s" % filename)

        return data

    def makeTask(self, procDefs):
        # Blow away any cached config data
        if 'devicename' in ZenProcessTask.DEVICE_STATS:
            del ZenProcessTask.DEVICE_STATS['devicename']

        config = TaskConfig(procDefs=procDefs)
        task = ZenProcessTask('bogodevice', 'taskname', 0, config)

        task._preferences = Preferences()
        task._preferences.options.showrawtables = False
        task._preferences.options.showprocs = False
        task._preferences.options.captureFilePrefix = ''
        task._eventService = EventService()
        return task

    def expected(self, PROCESSES=None, AFTERBYCONFIG=None, AFTERPIDTOPS=None, BEFOREBYCONFIG=None,
                 NEW=None, RESTARTED=None, DEAD=None, MISSING=None):
        testValues = {}

        for key in ProcessResults.orderedKeys:
            arg = locals()[key]
            if arg is not None:
                testValues[key] = arg
                
        return testValues

    def compareTestFile(self, filename, task, expectedStats):
        """
        Assert that the results of running zenprocess on a specified test data
        file match the expectation.

        filename --- the name of a file in Products/ZenRRD/tests/zenprocess_data that
            conforms to the format expected by compareTestData
        task --- the Products.ZenRRD.zenprocess.ZenProcessTask to use when 
            processing the data
        expectedStats --- tuple containing numbers for the following: procs, 
            afterByConfig, afterPidToProcessStats, beforeByConfig, newPids, restarted

        The results are passed back from the method
        """
        data = self.getFileData(filename)
        return self.compareTestData(data, task, expectedStats)

    def compareTestData(self, data, task, expected):
        """
        Assert that the results of running zenprocess on the specified test data
        matches the expectation.

        testName --- the name of the running test, used for error logging
        data --- a dictionary that conforms to the following format: 
                dict(snmpCategory->dict(snmpOID->data)):
                {'.1.3.6.1.2.1.25.4.2.1.2': {'.1.3.6.1.2.1.25.4.2.1.2.<PID>': <process name>},
                 '.1.3.6.1.2.1.25.4.2.1.4': {'.1.3.6.1.2.1.25.4.2.1.4.<PID>': <process full path>},
                 '.1.3.6.1.2.1.25.4.2.1.5': {'.1.3.6.1.2.1.25.4.2.1.5.<PID>': <arguments>}}
            I.e.:
                {'.1.3.6.1.2.1.25.4.2.1.2': {'.1.3.6.1.2.1.25.4.2.1.2.3127': 'mingetty'},
                 '.1.3.6.1.2.1.25.4.2.1.4': {'.1.3.6.1.2.1.25.4.2.1.4.3127': '/sbin/mingetty'},
                 '.1.3.6.1.2.1.25.4.2.1.5': {'.1.3.6.1.2.1.25.4.2.1.5.3127': 'tty1'}}
        task --- the Products.ZenRRD.zenprocess.ZenProcessTask to use when 
            processing the data
        expected --- dictionary containing numbers for any/all of the keys defined in ProcessResults

        The results are passed back from the method
        """
        procs = task._parseProcessNames(data)
        results = task._determineProcessStatus(procs)

        actual = dict(zip(ProcessResults.resultKeys, results))
        actual[ProcessResults.PROCESSES] = procs

        # Save the results of the run
        task._deviceStats._pidToProcess = actual[ProcessResults.AFTERPIDTOPS]

        for key in expected:
            if expected[key] is not None:
                self.assert_(key in actual, "No results found for key %s, expected %d" %
                            (key, expected[key]))
                self.assert_(len(actual[key]) == expected[key], "Expected %d %s, got %d (%s)" %
                            (expected[key], key, len(actual[key]), actual[key]))

        # Return back the results in case somebody wants to dive in
        return actual

    def updateProcDefs(self, procDefs, name, ignoreParams, regex):
        procDef = ProcessProxy()
        procDef.name = name if len(name.split(' ')) > 1 else getProcessIdentifier(name, '')
        procDef.regex = re.compile(regex)
        procDef.ignoreParameters = ignoreParams
        procDefs[procDef.name] = procDef

    def getProcDefsFromFile(self, procDefFile):
        """
        Expects to read a file that's a dump of

        python ProcessConfig.py --device=XX

        The file should be trimmed to remove any headers, and just contain config output
        """
        base = zenPath('Products/ZenRRD/tests/zenprocess_data')
        procDefs = {}
        name = base + '/' + procDefFile
        try:
            for line in open(name).readlines():
                modeler_match, useArgs, regex = line.rsplit(None, 2)
                useArgs = True if useArgs.strip() == 'True' else False
                self.updateProcDefs(procDefs, modeler_match.strip(), useArgs, regex.strip())
        except Exception, ex:
            log.warn('Unable to evaluate data file %s because %s',
                     name, str(ex))
        return procDefs

    def getSingleProcessTask(self, ignoreArgs=False):
        procDefs = {}
        procName = 'testProcess' if ignoreArgs else getProcessIdentifier('testProcess', 'args')
        self.updateProcDefs(procDefs, procName, ignoreArgs, '/fake/path/testProcess')
        task = self.makeTask(procDefs)

        #Sanity check our definition with a valid data run
        data = {'.1.3.6.1.2.1.25.4.2.1.2': {'.1.3.6.1.2.1.25.4.2.1.2.1': 'testProcess'},
                '.1.3.6.1.2.1.25.4.2.1.4': {'.1.3.6.1.2.1.25.4.2.1.4.1': '/fake/path/testProcess'},
                '.1.3.6.1.2.1.25.4.2.1.5': {'.1.3.6.1.2.1.25.4.2.1.5.1': 'args'}}
        self.compareTestData(data, task, self.expected(PROCESSES=1))
        
        return task

    def testProcessCountIgnoreParams(self):
        task = self.getSingleProcessTask(ignoreArgs=True)

        data = {'.1.3.6.1.2.1.25.4.2.1.2': {'.1.3.6.1.2.1.25.4.2.1.2.1': 'testProcess',
                                            '.1.3.6.1.2.1.25.4.2.1.2.2': 'testProcess',
                                            '.1.3.6.1.2.1.25.4.2.1.2.3': 'testProcess',
                                            '.1.3.6.1.2.1.25.4.2.1.2.4': 'testProcess'},
                '.1.3.6.1.2.1.25.4.2.1.4': {'.1.3.6.1.2.1.25.4.2.1.4.1': '/fake/path/testProcess',
                                            '.1.3.6.1.2.1.25.4.2.1.4.2': '/fake/path/testProcess',
                                            '.1.3.6.1.2.1.25.4.2.1.4.3': '/fake/path/testProcess',
                                            '.1.3.6.1.2.1.25.4.2.1.4.4': '/fake/path/testProcess'},
                '.1.3.6.1.2.1.25.4.2.1.5': {'.1.3.6.1.2.1.25.4.2.1.5.1': '1',
                                            '.1.3.6.1.2.1.25.4.2.1.5.2': '2',
                                            '.1.3.6.1.2.1.25.4.2.1.5.3': '3',
                                            '.1.3.6.1.2.1.25.4.2.1.5.4': '4'}}
        self.compareTestData(data, task, self.expected(PROCESSES=4))

    def testProcessCount(self):
        task = self.getSingleProcessTask(ignoreArgs=False)

        data = {'.1.3.6.1.2.1.25.4.2.1.2': {'.1.3.6.1.2.1.25.4.2.1.2.1': 'testProcess',
                                            '.1.3.6.1.2.1.25.4.2.1.2.2': 'testProcess',
                                            '.1.3.6.1.2.1.25.4.2.1.2.3': 'testProcess',
                                            '.1.3.6.1.2.1.25.4.2.1.2.4': 'testProcess'},
                '.1.3.6.1.2.1.25.4.2.1.4': {'.1.3.6.1.2.1.25.4.2.1.4.1': '/fake/path/testProcess',
                                            '.1.3.6.1.2.1.25.4.2.1.4.2': '/fake/path/testProcess',
                                            '.1.3.6.1.2.1.25.4.2.1.4.3': '/fake/path/testProcess',
                                            '.1.3.6.1.2.1.25.4.2.1.4.4': '/fake/path/testProcess'},
                '.1.3.6.1.2.1.25.4.2.1.5': {'.1.3.6.1.2.1.25.4.2.1.5.1': '1',
                                            '.1.3.6.1.2.1.25.4.2.1.5.2': '2',
                                            '.1.3.6.1.2.1.25.4.2.1.5.3': '3',
                                            '.1.3.6.1.2.1.25.4.2.1.5.4': '4'}}
        # Process count is not dependent on actual matching, just on the SNMP data returned.
        self.compareTestData(data, task, self.expected(PROCESSES=4))

    def testMissingNoMatchIgnoreParams(self):
        task = self.getSingleProcessTask(ignoreArgs=True)

        data = {'.1.3.6.1.2.1.25.4.2.1.2': {'.1.3.6.1.2.1.25.4.2.1.2.9': 'otherProcess'},
                '.1.3.6.1.2.1.25.4.2.1.4': {'.1.3.6.1.2.1.25.4.2.1.4.9': '/non/matching/otherProcess'},
                '.1.3.6.1.2.1.25.4.2.1.5': {'.1.3.6.1.2.1.25.4.2.1.5.9': 'other'}}
        self.compareTestData(data, task, self.expected(MISSING=1))

    def testMissingNoMatch(self):
        task = self.getSingleProcessTask(ignoreArgs=False)

        data = {'.1.3.6.1.2.1.25.4.2.1.2': {'.1.3.6.1.2.1.25.4.2.1.2.9': 'otherProcess'},
                '.1.3.6.1.2.1.25.4.2.1.4': {'.1.3.6.1.2.1.25.4.2.1.4.9': '/non/matching/otherProcess'},
                '.1.3.6.1.2.1.25.4.2.1.5': {'.1.3.6.1.2.1.25.4.2.1.5.9': ''}}
        self.compareTestData(data, task, self.expected(MISSING=1))

    def testMissingMismatchNameIgnoreParams(self):
        task = self.getSingleProcessTask(ignoreArgs=True)

        data = {'.1.3.6.1.2.1.25.4.2.1.2': {'.1.3.6.1.2.1.25.4.2.1.2.1': 'WRONGNAME'},
                '.1.3.6.1.2.1.25.4.2.1.4': {'.1.3.6.1.2.1.25.4.2.1.4.1': '/fake/path/testProcess'},
                '.1.3.6.1.2.1.25.4.2.1.5': {'.1.3.6.1.2.1.25.4.2.1.5.1': 'args'}}
        self.compareTestData(data, task, self.expected(MISSING=0))

    def testMissingMismatchName(self):
        task = self.getSingleProcessTask(ignoreArgs=False)

        data = {'.1.3.6.1.2.1.25.4.2.1.2': {'.1.3.6.1.2.1.25.4.2.1.2.1': 'WRONGNAME'},
                '.1.3.6.1.2.1.25.4.2.1.4': {'.1.3.6.1.2.1.25.4.2.1.4.1': '/fake/path/testProcess'},
                '.1.3.6.1.2.1.25.4.2.1.5': {'.1.3.6.1.2.1.25.4.2.1.5.1': 'args'}}
        self.compareTestData(data, task, self.expected(MISSING=0))

    def testMissingMismatchNameNoArgs(self):
        procDefs = {}
        self.updateProcDefs(procDefs, getProcessIdentifier('testProcess1', ''), False, 'testProc')
        self.updateProcDefs(procDefs, getProcessIdentifier('testProcess2', ''), False, 'testProc')
        task = self.makeTask(procDefs)

        data = {'.1.3.6.1.2.1.25.4.2.1.2': {'.1.3.6.1.2.1.25.4.2.1.2.1': 'testProcess1',
                                            '.1.3.6.1.2.1.25.4.2.1.2.2': 'testProcess2'},
                '.1.3.6.1.2.1.25.4.2.1.4': {'.1.3.6.1.2.1.25.4.2.1.4.1': 'testProcess1',
                                            '.1.3.6.1.2.1.25.4.2.1.4.2': 'testProcess2'},
                '.1.3.6.1.2.1.25.4.2.1.5': {'.1.3.6.1.2.1.25.4.2.1.5.1': '',
                                            '.1.3.6.1.2.1.25.4.2.1.5.2': ''}}
        self.compareTestData(data, task, self.expected(PROCESSES=2, AFTERBYCONFIG=2, MISSING=0))

    def testMissingMismatchPathIgnoreParams(self):
        task = self.getSingleProcessTask(ignoreArgs=True)

        data = {'.1.3.6.1.2.1.25.4.2.1.2': {'.1.3.6.1.2.1.25.4.2.1.2.1': 'testProcess'},
                '.1.3.6.1.2.1.25.4.2.1.4': {'.1.3.6.1.2.1.25.4.2.1.4.1': '/WRONG/PATH'},
                '.1.3.6.1.2.1.25.4.2.1.5': {'.1.3.6.1.2.1.25.4.2.1.5.1': 'args'}}
        self.compareTestData(data, task, self.expected(MISSING=1))

    def testMissingMismatchPath(self):
        task = self.getSingleProcessTask(ignoreArgs=False)

        data = {'.1.3.6.1.2.1.25.4.2.1.2': {'.1.3.6.1.2.1.25.4.2.1.2.1': 'testProcess'},
                '.1.3.6.1.2.1.25.4.2.1.4': {'.1.3.6.1.2.1.25.4.2.1.4.1': '/WRONG/PATH'},
                '.1.3.6.1.2.1.25.4.2.1.5': {'.1.3.6.1.2.1.25.4.2.1.5.1': 'args'}}
        self.compareTestData(data, task, self.expected(MISSING=1))

    def testMissingMismatchArgsIgnoreParams(self):
        task = self.getSingleProcessTask(ignoreArgs=True)

        data = {'.1.3.6.1.2.1.25.4.2.1.2': {'.1.3.6.1.2.1.25.4.2.1.2.1': 'testProcess'},
                '.1.3.6.1.2.1.25.4.2.1.4': {'.1.3.6.1.2.1.25.4.2.1.4.1': '/fake/path/testProcess'},
                '.1.3.6.1.2.1.25.4.2.1.5': {'.1.3.6.1.2.1.25.4.2.1.5.1': 'WRONGARGS'}}
        self.compareTestData(data, task, self.expected(MISSING=0))

    def testMissingMismatchArgs(self):
        task = self.getSingleProcessTask(ignoreArgs=False)

        data = {'.1.3.6.1.2.1.25.4.2.1.2': {'.1.3.6.1.2.1.25.4.2.1.2.1': 'testProcess'},
                '.1.3.6.1.2.1.25.4.2.1.4': {'.1.3.6.1.2.1.25.4.2.1.4.1': '/fake/path/testProcess'},
                '.1.3.6.1.2.1.25.4.2.1.5': {'.1.3.6.1.2.1.25.4.2.1.5.1': 'WRONGARGS'}}
        #TODO: INCORRECT FUNCTIONALITY: Clearly one should be missing here. The process has
        #      non-matching arguments. The lax matching after a failure is the culprit.
        #self.compareTestData(data, task, self.expected(MISSING=1))

    def testMissingMismatchPidIgnoreParams(self):
        task = self.getSingleProcessTask(ignoreArgs=True)

        data = {'.1.3.6.1.2.1.25.4.2.1.2': {'.1.3.6.1.2.1.25.4.2.1.2.999': 'testProcess'},
                '.1.3.6.1.2.1.25.4.2.1.4': {'.1.3.6.1.2.1.25.4.2.1.4.999': '/fake/path/testProcess'},
                '.1.3.6.1.2.1.25.4.2.1.5': {'.1.3.6.1.2.1.25.4.2.1.5.999': 'args'}}
        # a mismatched PID is just a restarted process, not actually missing
        self.compareTestData(data, task, self.expected(MISSING=0))

    def testMissingMismatchPid(self):
        task = self.getSingleProcessTask(ignoreArgs=False)

        data = {'.1.3.6.1.2.1.25.4.2.1.2': {'.1.3.6.1.2.1.25.4.2.1.2.999': 'testProcess'},
                '.1.3.6.1.2.1.25.4.2.1.4': {'.1.3.6.1.2.1.25.4.2.1.4.999': '/fake/path/testProcess'},
                '.1.3.6.1.2.1.25.4.2.1.5': {'.1.3.6.1.2.1.25.4.2.1.5.999': 'args'}}
        # a mismatched PID is just a restarted process, not actually missing
        self.compareTestData(data, task, self.expected(MISSING=0))

    def testMultipleMissingIgnoreParams(self):
        procDefs = {}
        self.updateProcDefs(procDefs, 'testFirst',  True, '/fake/path/testFirst')
        self.updateProcDefs(procDefs, 'testSecond', True, '/fake/path/testSecond')
        self.updateProcDefs(procDefs, 'testThird',  True, '/fake/path/testThird')
        self.updateProcDefs(procDefs, 'testFourth', True, '/fake/path/testFourth')
        self.updateProcDefs(procDefs, 'testFifth',  True, '/fake/path/testFifth')
        task = self.makeTask(procDefs)

        data = {'.1.3.6.1.2.1.25.4.2.1.2': {'.1.3.6.1.2.1.25.4.2.1.2.1': 'testFirst',
                                            '.1.3.6.1.2.1.25.4.2.1.2.2': 'testSecond',
                                            '.1.3.6.1.2.1.25.4.2.1.2.3': 'testThird',
                                            '.1.3.6.1.2.1.25.4.2.1.2.4': 'testFourth',
                                            '.1.3.6.1.2.1.25.4.2.1.2.5': 'testFifth',},
                '.1.3.6.1.2.1.25.4.2.1.4': {'.1.3.6.1.2.1.25.4.2.1.4.1': '/fake/path/testFirst',
                                            '.1.3.6.1.2.1.25.4.2.1.4.2': '/fake/path/testSecond',
                                            '.1.3.6.1.2.1.25.4.2.1.4.3': '/fake/path/testThird',
                                            '.1.3.6.1.2.1.25.4.2.1.4.4': '/fake/path/testFourth',
                                            '.1.3.6.1.2.1.25.4.2.1.4.5': '/fake/path/testFifth'},
                '.1.3.6.1.2.1.25.4.2.1.5': {'.1.3.6.1.2.1.25.4.2.1.5.1': 'some',
                                            '.1.3.6.1.2.1.25.4.2.1.5.2': 'args',
                                            '.1.3.6.1.2.1.25.4.2.1.5.3': 'went',
                                            '.1.3.6.1.2.1.25.4.2.1.5.4': 'here',
                                            '.1.3.6.1.2.1.25.4.2.1.5.5': 'five'}}
        self.compareTestData(data, task, self.expected(PROCESSES=5, MISSING=0))

        data = {'.1.3.6.1.2.1.25.4.2.1.2': {'.1.3.6.1.2.1.25.4.2.1.2.1': 'WRONGPROCESS',
                                            '.1.3.6.1.2.1.25.4.2.1.2.2': 'testSecond',
                                            '.1.3.6.1.2.1.25.4.2.1.2.4': 'testFourth',
                                            '.1.3.6.1.2.1.25.4.2.1.2.99':'testFifth'},
                '.1.3.6.1.2.1.25.4.2.1.4': {'.1.3.6.1.2.1.25.4.2.1.4.1': '/fake/path/testFirst',
                                            '.1.3.6.1.2.1.25.4.2.1.4.2': '/fake/path/WRONGPATH',
                                            '.1.3.6.1.2.1.25.4.2.1.4.4': '/fake/path/testFourth',
                                            '.1.3.6.1.2.1.25.4.2.1.4.99':'/fake/path/testFifth'},
                '.1.3.6.1.2.1.25.4.2.1.5': {'.1.3.6.1.2.1.25.4.2.1.5.1': 'some',
                                            '.1.3.6.1.2.1.25.4.2.1.5.2': 'args',
                                            '.1.3.6.1.2.1.25.4.2.1.5.4': 'WRONGARGS',
                                            '.1.3.6.1.2.1.25.4.2.1.5.99':'five'}}
        self.compareTestData(data, task, self.expected(MISSING=2))

    def testMultipleMissing(self):
        procDefs = {}
        self.updateProcDefs(procDefs, getProcessIdentifier('testFirst',  'some'), False, '/fake/path/testFirst')
        self.updateProcDefs(procDefs, getProcessIdentifier('testSecond', 'args'), False, '/fake/path/testSecond')
        self.updateProcDefs(procDefs, getProcessIdentifier('testThird',  'went'), False, '/fake/path/testThird')
        self.updateProcDefs(procDefs, getProcessIdentifier('testFourth', 'here'), False, '/fake/path/testFourth')
        self.updateProcDefs(procDefs, getProcessIdentifier('testFifth',  'five'), False, '/fake/path/testFifth')
        task = self.makeTask(procDefs)
        
        data = {'.1.3.6.1.2.1.25.4.2.1.2': {'.1.3.6.1.2.1.25.4.2.1.2.1': 'testFirst',
                                            '.1.3.6.1.2.1.25.4.2.1.2.2': 'testSecond',
                                            '.1.3.6.1.2.1.25.4.2.1.2.3': 'testThird',
                                            '.1.3.6.1.2.1.25.4.2.1.2.4': 'testFourth',
                                            '.1.3.6.1.2.1.25.4.2.1.2.5': 'testFifth',},
                '.1.3.6.1.2.1.25.4.2.1.4': {'.1.3.6.1.2.1.25.4.2.1.4.1': '/fake/path/testFirst',
                                            '.1.3.6.1.2.1.25.4.2.1.4.2': '/fake/path/testSecond',
                                            '.1.3.6.1.2.1.25.4.2.1.4.3': '/fake/path/testThird',
                                            '.1.3.6.1.2.1.25.4.2.1.4.4': '/fake/path/testFourth',
                                            '.1.3.6.1.2.1.25.4.2.1.4.5': '/fake/path/testFifth'},
                '.1.3.6.1.2.1.25.4.2.1.5': {'.1.3.6.1.2.1.25.4.2.1.5.1': 'some',
                                            '.1.3.6.1.2.1.25.4.2.1.5.2': 'args',
                                            '.1.3.6.1.2.1.25.4.2.1.5.3': 'went',
                                            '.1.3.6.1.2.1.25.4.2.1.5.4': 'here',
                                            '.1.3.6.1.2.1.25.4.2.1.5.5': 'five'}}
        self.compareTestData(data, task, self.expected(PROCESSES=5, MISSING=0))

        data = {'.1.3.6.1.2.1.25.4.2.1.2': {'.1.3.6.1.2.1.25.4.2.1.2.1': 'WRONGPROCESS',
                                            '.1.3.6.1.2.1.25.4.2.1.2.2': 'testSecond',
                                            '.1.3.6.1.2.1.25.4.2.1.2.4': 'testFourth',
                                            '.1.3.6.1.2.1.25.4.2.1.2.99':'testFifth'},
                '.1.3.6.1.2.1.25.4.2.1.4': {'.1.3.6.1.2.1.25.4.2.1.4.1': '/fake/path/testFirst',
                                            '.1.3.6.1.2.1.25.4.2.1.4.2': '/fake/path/WRONGPATH',
                                            '.1.3.6.1.2.1.25.4.2.1.4.4': '/fake/path/testFourth',
                                            '.1.3.6.1.2.1.25.4.2.1.4.99':'/fake/path/testFifth'},
                '.1.3.6.1.2.1.25.4.2.1.5': {'.1.3.6.1.2.1.25.4.2.1.5.1': 'some',
                                            '.1.3.6.1.2.1.25.4.2.1.5.2': 'args',
                                            '.1.3.6.1.2.1.25.4.2.1.5.4': 'WRONGARGS',
                                            '.1.3.6.1.2.1.25.4.2.1.5.99':'five'}}
        #TODO: INCORRECT FUNCTIONALITY: Clearly more than two should be missing here. In particular, the process testFourth has
        #      non-matching arguments. The lax matching after a failure is the culprit.
        #self.compareTestData(data, task, self.expected(MISSING=3))

    def testMingetty(self):
        """
        Sanity check for simplified example
        """
        procDefs = {}
        self.updateProcDefs(procDefs, 'mingetty', True, '/sbin/mingetty')
        mingetty = procDefs[getProcessIdentifier('mingetty', '')]
        task = self.makeTask(procDefs)

        expectedStats = self.expected(6, 1, 6, 0, 6, 0, 0, 0)
        self.compareTestFile('mingetty-0', task, expectedStats)

        # No changes if there are no changes
        expectedStats = self.expected(6, 1, 6, 1, 0, 0, 0, 0)
        self.compareTestFile('mingetty-0', task, expectedStats)

        # Note: the restart count is only used if we want to
        #       receive notifications
        expectedStats = self.expected(6, 1, 6, 1, 1, 0, 1, 0)
        self.compareTestFile('mingetty-1', task, expectedStats)

        mingetty.restart = True
        expectedStats = self.expected(6, 1, 6, 1, 1, 1, 1, 0)
        self.compareTestFile('mingetty-0', task, expectedStats)

    def testCase15875part1(self):
        procDefs = {}
        self.updateProcDefs(procDefs, getProcessIdentifier('syslogd', '-m 0'), False, '^syslogd')
        self.updateProcDefs(procDefs, getProcessIdentifier('usr_bin_perl', '-w /opt/sysadmin/packages/scooper/bin/scooperd /opt/sysadmin/packages/scooper/config/config.xml /opt/sysadmin/packages/scooper/config/sanity.xml'), False, '^.*?/usr/bin/perl\s+-w\s+/opt/sysadmin/packages/scooper/bin/scooperd\s+/opt.*')
        self.updateProcDefs(procDefs, getProcessIdentifier('usr_java_jdk_bin_java', '-Djava.awt.headless=true -Djava.endorsed.dirs=/opt/gsp/nationwideUKFraudCard-cqa/tomcat/common/endorsed -classpath /usr/java/jdk/lib/tools.jar:/opt/gsp/nationwideUKFraudCard-cqa/tomcat/bin/bootstrap.jar:/opt/gsp/nationwideUKFraudCard-cqa/tomcat/bin/commons-logging-api.jar -Dcatalina.base=/opt/gsp/nationwideUKFraudCard-cqa/tomcat -Dcatalina.home=/opt/gsp/nationwideUKFraudCard-cqa/tomcat -Djava.io.tmpdir=/opt/gsp/nationwideUKFraudCard-cqa/tomcat/temp org.apache.catalina.startup.Bootstrap start'), False, '/opt/gsp/')
        self.updateProcDefs(procDefs, getProcessIdentifier('ntpd', '-u ntp:ntp -p /var/run/ntpd.pid'), False, '^ntpd')
        self.updateProcDefs(procDefs, getProcessIdentifier('perl', './aSecure.pl -d'), False, 'aSecure\.rb|aSecure\.pl')
        self.updateProcDefs(procDefs, 'crond', True, '^crond')

        task = self.makeTask(procDefs)
        expectedStats = self.expected(117, 6, 7, 0, 7, 0, 0, 0)
        self.compareTestFile('case15875-0', task, expectedStats)

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
        expectedStats = self.expected(97, 3, 3, 0, 3, 0, 0, 0)
        self.compareTestFile('case15875-1', task, expectedStats)

        # Now what happens when the remote agent screws up a bit
        # and *ALMOST* sends us all the stuff?
        expectedStats = self.expected(97, 3, 3, 3, 0, 0, 0, 0)
        results = self.compareTestFile('case15875-2', task, expectedStats)
        deadPids = results[ProcessResults.DEAD]
        
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
        expectedStats = self.expected(174, 31, 52, 0, 52, 0, 0, 0)
        self.compareTestFile('case15875-3', task, expectedStats)

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
        expectedStats = self.expected(253, 7, 15, 0, 15, 0, 0, 0)
        self.compareTestFile('case15875-4', task, expectedStats)

    def testRemodels(self):
        procDefs = self.getProcDefsFromFile('remodel_bug-config-0')
        task = self.makeTask(procDefs)
        expectedStats = self.expected(159, 29, 31, 0, 31, 0, 0, 2)
        self.compareTestFile('remodel_bug-0', task, expectedStats)

        procDefs = self.getProcDefsFromFile('remodel_bug-config-1')
        expectedStats = self.expected(157, 30, 32, 4, 28, 0, 0, 1)
        config = TaskConfig(procDefs=procDefs)
        task._deviceStats.update(config)
        self.compareTestFile('remodel_bug-1', task, expectedStats)

    def testSubsetCorrectMatch(self):
        procDefs = {}
        self.updateProcDefs(procDefs, 'rpciod_3', False, 'rpc')
        self.updateProcDefs(procDefs, 'rpciod_32', False, 'rpc')
        task = self.makeTask(procDefs)

        data = {'.1.3.6.1.2.1.25.4.2.1.2': {'.1.3.6.1.2.1.25.4.2.1.2.1': 'rpciod/3',
                                            '.1.3.6.1.2.1.25.4.2.1.2.2': 'rpciod/32'},
                '.1.3.6.1.2.1.25.4.2.1.4': {'.1.3.6.1.2.1.25.4.2.1.4.1': 'rpciod/3',
                                            '.1.3.6.1.2.1.25.4.2.1.4.2': 'rpciod/32'},
                '.1.3.6.1.2.1.25.4.2.1.5': {'.1.3.6.1.2.1.25.4.2.1.5.1': '',
                                            '.1.3.6.1.2.1.25.4.2.1.5.2': ''}}
        self.compareTestData(data, task, self.expected(PROCESSES=2, AFTERBYCONFIG=2, MISSING=0))

    def testSuffixCorrectMatch(self):
        procDefs = {}
        self.updateProcDefs(procDefs, 'iod_3', False, 'iod')
        self.updateProcDefs(procDefs, 'ciod_3', False, 'iod')
        self.updateProcDefs(procDefs, 'pciod_3', False, 'iod')
        self.updateProcDefs(procDefs, 'rpciod_3', False, 'iod')
        task = self.makeTask(procDefs)

        data = {'.1.3.6.1.2.1.25.4.2.1.2': {'.1.3.6.1.2.1.25.4.2.1.2.1': 'iod/3',
                                            '.1.3.6.1.2.1.25.4.2.1.2.2': 'ciod/3',
                                            '.1.3.6.1.2.1.25.4.2.1.2.3': 'pciod/3',
                                            '.1.3.6.1.2.1.25.4.2.1.2.4': 'rpciod/3'},
                '.1.3.6.1.2.1.25.4.2.1.4': {'.1.3.6.1.2.1.25.4.2.1.4.1': '/etc/iod/3',
                                            '.1.3.6.1.2.1.25.4.2.1.4.2': '/etc/ciod/3',
                                            '.1.3.6.1.2.1.25.4.2.1.4.3': '/etc/pciod/3',
                                            '.1.3.6.1.2.1.25.4.2.1.4.4': '/etc/rpciod/3'},
                '.1.3.6.1.2.1.25.4.2.1.5': {'.1.3.6.1.2.1.25.4.2.1.5.1': '',
                                            '.1.3.6.1.2.1.25.4.2.1.5.2': '',
                                            '.1.3.6.1.2.1.25.4.2.1.5.3': '',
                                            '.1.3.6.1.2.1.25.4.2.1.5.4': ''}}
        self.compareTestData(data, task, self.expected(PROCESSES=4, AFTERBYCONFIG=4, MISSING=0))

    def testRpciods(self):
        procDefs = self.getProcDefsFromFile('rpciod_test_config')
        task = self.makeTask(procDefs)
        self.compareTestFile('rpciod_test', task, self.expected(PROCESSES=33, NEW=33, MISSING=0))

    def testSpecialCharacterSuffix(self):
        procDefs = {}
        self.updateProcDefs(procDefs, 'sendmail_', False, 'sendmail: accepting connections')
        task = self.makeTask(procDefs)

        data = {'.1.3.6.1.2.1.25.4.2.1.2': {'.1.3.6.1.2.1.25.4.2.1.2.1': 'sendmail: accepting connections'},
                '.1.3.6.1.2.1.25.4.2.1.4': {'.1.3.6.1.2.1.25.4.2.1.4.1': 'sendmail: accepting connections'},
                '.1.3.6.1.2.1.25.4.2.1.5': {'.1.3.6.1.2.1.25.4.2.1.5.1': ''}}
        
        self.compareTestData(data, task, self.expected(PROCESSES=1, AFTERBYCONFIG=1, MISSING=0))

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestZenprocess))
    return suite

