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
from Products.ZenModel.OSProcess import OSProcess

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
        log.info('HRSWRunMap Processing %s for device %s', self.name(), device.id)
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

        os_process_class_instances_to_match = self.generateCompiledRegexs(device.getOSProcessMatchers)
        found = []
        rm = self.relMap()
        
        for proc in pidtable.values():
            om = self.objectMap(proc)
            om.processText = proc['procName'] + ' ' + proc['parameters']
            ppath = getattr(om, '_procPath', False)
            if ppath and ppath.find('\\') == -1:
                om.processText = om._procPath + proc['parameters']
            if not getattr(om, 'processText', False):
                log.warn("Skipping process with no name")
                continue
            
            # os_process_classes_to_match = list of dictionaries containing OSProcessClass info
            # om = object map
            # found = list of processes that have been found
            # rm = rel map
            for os_process_class_instance in os_process_class_instances_to_match:
                if OSProcess.matchRegex(os_process_class_instance['compiledRegex'], os_process_class_instance['compiledExcludeRegex'], om.processText):
                    om.setOSProcessClass = os_process_class_instance['getPrimaryDmdId']
                    om.id = OSProcess.generateId(os_process_class_instance['compiledRegex'], os_process_class_instance['getPrimaryUrlPath'], om.processText)
                    if om.id not in found:
                        log.debug("om.id: %s" % om.id)
                        found.append(om.id)
                        rm.append(om)

        # return the now populated relmap
        return rm

    def generateCompiledRegexs(self, matchers):
        """
        copy the input 'matchers' and add two keys: compiledRegex and compiledExcludeRegex
        
        @parameter matchers: [{'regex': '.*runzope.*zenoss.*', 'excludeRegex': '.*runzzzope.*zenoss.*', 'getPrimaryDmdId': '/Processes/Zenoss/osProcessClasses/Zope'},
        @type name: list of dicts
        @return: parameter matchers + additional keys (specifically compiled regexs)
        @rtype: list of dicts
        """
        compiled_matchers = []
        for matcher in matchers:
            try:
                c_matcher = matcher.copy()
                c_matcher['compiledRegex'] = re.compile(matcher['regex'])
                c_matcher['compiledExcludeRegex'] = re.compile(matcher['excludeRegex'])
                compiled_matchers.append(c_matcher)
            except Exception:
                if 'regex' in matcher:
                    msg = "Invalid process regex '{0}' -- ignoring" \
                          .format(matcher['regex'])
                else:
                    msg = 'matcher is missing regex'
                self._log.warning(msg)
        return compiled_matchers
