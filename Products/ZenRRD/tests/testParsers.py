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
from Products.ZenRRD.tests.BaseParsersTestCase import Object
from Products.ZenRRD.CommandParser import ParsedResults


class TestPsParser(BaseTestCase):
    """
    A one-off test of the ps parser that does not use the data files.
    """
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
        from Products.ZenRRD.parsers.ps import ps
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


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestPsParser))
    return suite
