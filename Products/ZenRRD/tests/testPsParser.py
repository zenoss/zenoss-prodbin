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

from pprint import pprint

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenRRD.tests.BaseParsersTestCase import Object
from Products.ZenRRD.CommandParser import ParsedResults

from Products.ZenRRD.parsers.ps import ps

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
        p4.data = dict(processName='notherJob1',
                       ignoreParams=True,
                       alertOnRestart=False,
                       failSeverity=3)
        cmd.points = [p1, p2, p3, p4]
        cmd.result = Object()
        cmd.result.output = """  PID   RSS     TIME COMMAND
123 1 00:00:00 someJob a b c
234 1 00:00:00 anotherJob a b c
345 1 10:23 notherJob1 a b c
"""
        results = ParsedResults()
        parser = ps()
        parser.processResults(cmd, results)
        assert len(results.values)
        assert len(results.events) == 4
        # Check time of 10:23 equals 623 minutes
        #print "623 number = %s" % results.values[0][1]
        #assert results.values[0][1] == 623
        assert len([value for dp, value in results.values if value == 623]) == 1
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
            elif summary.find('notherJob') >= 0:
                assert summary.find('not running') >= 0
            else:
                raise AssertionError("unexpected event")

    def testPsCase10733(self):
        """
        Case 10733
        """
        deviceConfig = Object()
        deviceConfig.device = 'localhost'
        cmd = Object()
        cmd.deviceConfig = deviceConfig
        p1 = Object()
        p1.id = 'cpu_cpu'
        p1.data = dict(processName='bogoApplication --conf bogo.conf instance4',
                       ignoreParams=False,
                       alertOnRestart=True,
                       failSeverity=3)
        p2 = Object()
        p2.id = 'mem_mem'
        p2.data = dict(processName='bogoApplication --conf bogo.conf instance4',
                       ignoreParams=False,
                       alertOnRestart=True,
                       failSeverity=3)
        p3 = Object()
        p3.id = 'count_count'
        p3.data = dict(processName='bogoApplication --conf bogo.conf instance4',
                       ignoreParams=False,
                       alertOnRestart=True,
                       failSeverity=3)
        p4 = Object()
        p4.id = 'count_count'
        p4.data = dict(processName='bogoApplication',
                       ignoreParams=True,
                       alertOnRestart=True,
                       failSeverity=3)
        cmd.points = [p1, p2, p3, p4]
        cmd.result = Object()
        cmd.result.output = """ PID   RSS        TIME COMMAND
483362 146300    22:58:11 /usr/local/bin/bogoApplication --conf bogo.conf instance5
495844 137916    22:45:57 /usr/local/bin/bogoApplication --conf bogo.conf instance6
508130 138196    22:23:08 /usr/local/bin/bogoApplication --conf bogo.conf instance3
520290  1808    00:00:00 /usr/sbin/aixmibd 
561300 140440    22:13:15 /usr/local/bin/bogoApplication --conf bogo.conf instance4
561301 140440    22:13:15 /usr/local/bin/bogoApplication --conf bogo.conf instance4
561302 140440    22:13:15 /usr/local/bin/wrapper bogoApplication --conf bogo.conf instance4
749772  3652    00:00:00 /bin/nmon_aix53 -f -A -P -V -m /tmp 
"""
        results = ParsedResults()
        parser = ps()
        parser.processResults(cmd, results)
        self.assertEquals(len(results.values), 4)
        self.assertEquals(len(results.events), 2)
        self.assertEquals(results.events[0]['severity'], 0)
        for dp, value in results.values:
            if 'count' in dp.id:
                if dp.data['processName'] == 'bogoApplication':
                    self.assertEquals(value, 5)
                else:
                    self.assertEquals(value, 3)
            elif 'cpu' in dp.id:
                self.assertEquals(value, 239985.0)
            elif 'mem' in dp.id:
                self.assertEquals(value, 421320.0)
            else:
                raise AssertionError("unexpected value")


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestParsers))
    return suite
