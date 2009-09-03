###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, 2009 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################


from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenRRD.tests.BaseParsersTestCase import Object
from Products.ZenRRD.CommandParser import ParsedResults


class TestParsers(BaseTestCase):
    def testPs(self):
        """
        A one-off test of the ps parser that does not use the data files.
        """
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
        p4 = Object()
        p4.id = 'cpu_cpu'
        p4.data = dict(processName='anotherJob1',
                       ignoreParams=True,
                       alertOnRestart=False,
                       failSeverity=3)
        cmd.points = [p1, p2, p3, p4]
        cmd.result = Object()
        cmd.result.output = """  PID   RSS     TIME COMMAND
123 1 00:00:00 someJob a b c
234 1 00:00:00 anotherJob a b c
345 1 10:23 anotherJob1 a b c
"""
        results = ParsedResults()
        from Products.ZenRRD.parsers.ps import ps
        parser = ps()
        parser.processResults(cmd, results)
        assert len(results.values)
        assert len(results.events) == 4
        # Check time of 10:23 equals 623 minutes
        assert results.values[0][1] == 623
        assert len([ev for ev in results.events if ev['severity'] == 0]) == 3
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
        assert len(results.events) == 4
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

    def testCacti(self):
        deviceConfig = Object()
        deviceConfig.device = 'localhost'
        cmd = Object()
        cmd.deviceConfig = deviceConfig
        p1 = Object()
        p1.id = 'cacti_single_result'
        p1.data = dict(processName='someJob a b c',
                       ignoreParams=False,
                       alertOnRestart=True,
                       failSeverity=3)
        cmd.points = [p1]
        cmd.result = Object()
        cmd.result.output = "77"
        cmd.result.exitCode = 2
        cmd.severity = 2
        cmd.command = "testCactiPlugin"
        cmd.eventKey = "cactiKey"
        cmd.eventClass = "/Cmd"
        cmd.component = "zencommand"
        results = ParsedResults()
        from Products.ZenRRD.parsers.Cacti import Cacti
        parser = Cacti()
        parser.processResults(cmd, results)
        self.assertEquals( len(results.values), 1)
        self.assertEquals(77,  int(results.values[0][1]))

        # Now test multiple data points
        p2 = Object()
        p2.id = 'cacti_multi_result'
        p2.data = dict(processName='someJob a b c',
                       ignoreParams=False,
                       alertOnRestart=True,
                       failSeverity=3)
        cmd.points.append( p2 )
        cmd.result.output = "cacti_single_result:77 cacti_multi_result:21"
        results = ParsedResults()
        parser.processResults(cmd, results)
        self.assertEquals( len(results.values), 2)
        values = map(lambda x: x[1], results.values)
        self.assertTrue(77.0 in values)
        self.assertTrue(21.0 in values)

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestParsers))
    return suite
