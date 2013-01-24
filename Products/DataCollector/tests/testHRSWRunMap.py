##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import logging
import re
from unittest import TestCase, makeSuite
from Products.DataCollector.plugins.zenoss.snmp.HRSWRunMap import HRSWRunMap

log = logging.getLogger("zen.testcases")


class FakeObjectMap(object):

    procName = 'procName'
    parameters = 'parameters'


class FakeDevice(object):

    id = 'id'
    getOSProcessMatchers = [dict(regex='foo',
                                 getPrimaryDmdId='quux',
                                 ignoreParametersWhenModeling=False),
                           ]


def createHRSWRunMap():
    sw_run_map = HRSWRunMap()
    sw_run_map._log = log
    return sw_run_map


class TestHRSWRunMap(TestCase):

    def test_compile_matchers(self):
        sw_run_map = createHRSWRunMap()
        matchers = [dict(),  # matcher is missing regex
                    dict(regex=r'?'),  # Invalid process regex '?' -- ignoring
                    dict(regex=r'foo'),
                   ]
        actual = sw_run_map.compile_matchers(matchers)
        self.assert_(actual is not None)
        self.assertEqual(1, len(actual))
        self.assertEqual(r'foo', actual[0]['regex'])

    def test_match_and_append(self):
        sw_run_map = createHRSWRunMap()
        compiled_matchers = [
            dict(regex_search_function=re.compile(r'bar').search,
                 getPrimaryDmdId='quux',
                 ignoreParametersWhenModeling=False),
            dict(regex_search_function=re.compile(r'flim').search,
                 getPrimaryDmdId='flam',
                 ignoreParametersWhenModeling=True),
            dict(regex_search_function=re.compile(r'.*').search,
                 getPrimaryDmdId='floo',
                 ignoreParametersWhenModeling=True),
        ]
        om = FakeObjectMap()
        found = {}
        rm = []
        actual = sw_run_map.match_and_append(compiled_matchers, om, found, rm)
        self.assert_(actual is None)

    def test_process(self):
        sw_run_map = createHRSWRunMap()
        device = FakeDevice()
        getdata = {}

        # Unable to get data for .1.3.6.1.2.1.25.4.2.1 from hrSWRunEntry id
        # -- skipping model
        tabledata = {}
        results = [getdata, tabledata]
        actual = sw_run_map.process(device, results, log)
        self.assert_(actual is None, 'actual is not None: {0}'.format(actual))

        # No process information from hrSWRunEntry .1.3.6.1.2.1.25.4.2.1
        tabledata['hrSWRunEntry'] = {}
        actual = sw_run_map.process(device, results, log)
        self.assert_(actual is None, 'actual is not None: {0}'.format(actual))

        # Skipping process with no name
        procs = {'proc_key': 'proc_value'}
        tabledata['hrSWRunEntry'] = {'key': procs}
        actual = sw_run_map.process(device, results, log)
        self._assert_empty_rm(actual)

        procs = {'_procPath': '_procPath_value'}
        tabledata['hrSWRunEntry'] = {'key': procs}
        actual = sw_run_map.process(device, results, log)
        self._assert_empty_rm(actual)

    def _assert_empty_rm(self, rm):
        self.assert_(rm is not None)
        class_name = self._get_class_name(rm)
        self.assertEqual('RelationshipMap', class_name,
                         'Not a RelationshipMap: {0}'.format(class_name))
        self.assertEqual('os', rm.compname, 'Not os: {0}'.format(rm.compname))
        self.assertEqual('processes', rm.relname,
                         'Not processes: {0}'.format(rm.relname))
        self.assertEqual([], rm.maps)

    def _get_class_name(self, instance):
        class_ = getattr(instance, '__class__', None)
        if class_ is None:
            return None
        return class_.__name__


def test_suite():
    return makeSuite(TestHRSWRunMap)
