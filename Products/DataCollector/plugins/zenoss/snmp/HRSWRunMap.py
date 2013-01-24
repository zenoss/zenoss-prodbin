##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


"""HRSWRunMap

HRSWRunMap maps the processes running on the system to OSProcess objects.
Uses the HOST-RESOURCES-MIB OIDs.

"""

# This file has 100% unit test coverage. If you modify it be sure to maintain
# the 100% test coverage.
#
# $ easy_install coverage
# $ coverage run /opt/zenoss/bin/runtests -m testHRSWRunMap
# $ coverage report -m DataCollector/plugins/zenoss/snmp/HRSWRunMap.py
# Name                                           Stmts   Miss  Cover   Missing
# ----------------------------------------------------------------------------
# DataCollector/plugins/zenoss/snmp/HRSWRunMap      70      0   100%

import re
from Products.DataCollector.plugins.CollectorPlugin import SnmpPlugin, \
                                                           GetTableMap
from Products.ZenModel.OSProcess import getProcessIdentifier

HRSWRUNENTRY = '.1.3.6.1.2.1.25.4.2.1'


class HRSWRunMap(SnmpPlugin):

    maptype = "OSProcessMap"
    compname = "os"
    relname = "processes"
    modname = "Products.ZenModel.OSProcess"
    deviceProperties = SnmpPlugin.deviceProperties + ('getOSProcessMatchers',)

    columns = {
         '.2': 'procName',
         '.4': '_procPath',
         '.5': 'parameters',
         }

    snmpGetTableMaps = (
        GetTableMap('hrSWRunEntry', HRSWRUNENTRY, columns),
    )

    def process(self, device, results, log):
        """
        Process the SNMP information returned from a device
        """
        self._log = log
        log.info('Processing %s for device %s', self.name(), device.id)
        getdata, tabledata = results
        log.debug("%s tabledata = %s", device.id, tabledata)

        # get the SNMP process data
        pidtable = tabledata.get("hrSWRunEntry")
        if pidtable is None:
            log.error("Unable to get data for %s from hrSWRunEntry %s"
                          " -- skipping model", HRSWRUNENTRY, device.id)
            return None

        log.debug("=== Process information received ===")
        for p in sorted(pidtable.keys()):
            log.debug("snmpidx: %s\tprocess: %s" % (p, pidtable[p]))

        if not pidtable.values():
            log.warning("No process information from hrSWRunEntry %s",
                        HRSWRUNENTRY)
            return None

        compiled_matchers = self.compile_matchers(device.getOSProcessMatchers)
        found = {}
        rm = self.relMap()
        for proc in pidtable.values():
            om = self.objectMap(proc)
            ppath = getattr(om, '_procPath', False)
            if ppath and ppath.find('\\') == -1:
                om.procName = om._procPath
            if not getattr(om, 'procName', False):
                log.warn("Skipping process with no name")
                continue
            om.parameters = getattr(om, 'parameters', '')
            self.match_and_append(compiled_matchers, om, found, rm)
        return rm

    def compile_matchers(self, matchers):
        compiled_matchers = []
        for matcher in matchers:
            try:
                c_matcher = matcher.copy()
                c_matcher['regex_search_function'] = \
                                        re.compile(matcher['regex']).search
                compiled_matchers.append(c_matcher)
            except Exception:
                if 'regex' in matcher:
                    msg = "Invalid process regex '{0}' -- ignoring" \
                          .format(matcher['regex'])
                else:
                    msg = 'matcher is missing regex'
                self._log.warning(msg)
        return compiled_matchers

    def match_and_append(self, compiled_matchers, om, found, rm):
        for c_matcher in compiled_matchers:
            if c_matcher['ignoreParametersWhenModeling']:
                fullname = om.procName
                params = None
            else:
                fullname = (om.procName + ' ' + om.parameters).rstrip()
                params = om.parameters
            if not c_matcher['regex_search_function'](fullname):
                continue
            om.setOSProcessClass = c_matcher['getPrimaryDmdId']
            om.id = self.prepId(getProcessIdentifier(om.procName, params))
            if om.id not in found:
                found[om.id] = True
                rm.append(om)
            # Stop once a match is found.
            return
