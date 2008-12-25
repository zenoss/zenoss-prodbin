###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenRRD.CommandParser import ParsedResults

from Products.ZenRRD.parsers.ps import ps
from Products.ZenRRD.parsers.linux.df import df
from Products.ZenRRD.parsers.linux.dfi import dfi
from Products.ZenRRD.parsers.linux.ifconfig import ifconfig


import os, sys

from pprint import pprint, pformat


class Object(object): 
    
    def __repr__(self):
        return pformat(dict([(attr, getattr(self, attr)) for attr in dir(self) 
                if not attr.startswith('__')]))


def createPoints(expected):
    """
    Create data points for a ComponentCommandParser from a mapping of expected
    values.
    """
    points = []
    
    for componentScanValue in expected:
        data = dict(componentScanValue=componentScanValue)
        for id in expected[componentScanValue]:
            point = Object()
            point.id = id
            point.data = data
            point.expected = expected[componentScanValue][id]
            points.append(point)
            
    return points


class TestParsers(BaseTestCase):

    def testPs(self):
        deviceConfig = Object()
        deviceConfig.device = 'localhost'
        cmd = Object()
        cmd.deviceConfig = deviceConfig
        p1 = Object()
        p1.id = 'cpu_cpu'
        p1.data = dict(processName='someJob a b c',
                       ignoreParams=False,
                       alertOnRestart=True,
                       failSeverity=3)
        p2 = Object()
        p2.id = 'cpu_cpu'
        p2.data = dict(processName='noSuchProcess',
                       ignoreParams=True,
                       alertOnRestart=False,
                       failSeverity=1)
        p3 = Object()
        p3.id = 'cpu_cpu'
        p3.data = dict(processName='anotherJob',
                       ignoreParams=True,
                       alertOnRestart=False,
                       failSeverity=3)
        cmd.points = [p1, p2, p3]
        cmd.result = Object()
        cmd.result.output = """  PID   RSS     TIME COMMAND
123 1 00:00:00 someJob a b c
234 1 00:00:00 anotherJob a b c
"""
        results = ParsedResults()
        parser = ps()
        parser.processResults(cmd, results)
        assert len(results.values)
        assert len(results.events) == 3
        assert len([ev for ev in results.events if ev['severity'] == 0]) == 2
        assert len([ev for ev in results.events if ev['severity'] == 1]) == 1
        results = ParsedResults()
        cmd.result.output = """  PID   RSS     TIME COMMAND
124 1 00:00:00 someJob a b c
456 1 00:00:00 noSuchProcess
"""
        parser.processResults(cmd, results)
        assert len(results.values) == 2
        # anotherJob went down
        # someJob restarted
        # noSuchProcess started
        assert len(results.events) == 3
        for ev in results.events:
            summary = ev['summary']
            if summary.find('someJob') >= 0:
                assert summary.find('restarted') >= 0
            elif summary.find('noSuchProcess') >= 0:
                assert ev['severity'] == 0
            elif summary.find('anotherJob') >= 0:
                assert summary.find('not running') >= 0
            else:
                raise AssertionError("unexpected event")

    def _testParser(self, command, filename, Parser):
        datadir = "%s/data/linux/leak.zenoss.loc" % os.path.dirname(__file__)

        # read the data file
        datafile = open('%s/%s' % (datadir, filename))
        commandUsed = datafile.readline().rstrip("\n")
        self.assertEqual(command, commandUsed)
        output = "".join(datafile.readlines())
        datafile.close()
        
        # read the file containing the expected values
        expectedfile = open('%s/%s.py' % (datadir, filename))
        expected = eval("".join(expectedfile.readlines()))
        expectedfile.close()
        
        cmd = Object()
        cmd.points = createPoints(expected)
        cmd.result = Object()
        cmd.result.output = output
        results = ParsedResults()
        parser = Parser()
        parser.processResults(cmd, results)
        
        for value in results.values:
            self.assertEqual(value[0].expected, value[1])

        
    def test_df(self):
        self._testParser('/bin/df -Pk', '_bin_df_Pk', df)

    def test_dfi(self):
        self._testParser('/bin/df -iPk', '_bin_df_iPk', dfi)

    def test_ifconfig(self):
        self._testParser('/sbin/ifconfig -a', '_sbin_ifconfig_a', ifconfig)

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestParsers))
    return suite
