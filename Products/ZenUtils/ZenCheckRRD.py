#!/usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """
This command checks the RRD files on local and remote collectors to determine
the overall status of the data collection.  One status line per collector
is generated.

This command requires a file argument and can also send an event.
"""

import os
import re
from pickle import dump, load
from subprocess import Popen, PIPE
import logging
log = logging.getLogger('zen.checkRRD')

import Globals
import transaction
from Products.ZenUtils.Utils import zenPath
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.ZenEvents.ZenEventClasses import Status_Perf
from zenoss.protocols.protobufs.zep_pb2 import SEVERITY_CLEAR, SEVERITY_ERROR


CACHE_FILE = zenPath('var', 'zencheckrrd.cache')
rrdMatch = re.compile('DEF:[^=]+=([^:]+)').match


class collectorStats:
    def __init__(self, id, hostname):
        self.id = id
        self.hostname = hostname
        self.expectedComponents = 0
        self.stale = 0
        self.missing = 0
        self.orphan = 0
        self.expectedFiles = set()
        self.staleFiles = set()
        self.allFiles = set()


class ZenCheckRRD(ZenScriptBase):
    def __init__(self):
        ZenScriptBase.__init__(self, connect=True)

    def buildOptions(self):
        ZenScriptBase.buildOptions(self)
        self.parser.add_option('--age', dest='age',
            type='int', default=1,
            help="Number of days old to consider fresh (default=1)")
        self.parser.add_option('--all', dest='all',
            action="store_true", default=False,
            help="Check all data points. Not just ones used in graphs")
        self.parser.add_option('--pathcache', dest='pathcache',
            action="store_true", default=False,
            help="Cache the full list of RRD file paths in the model")
        self.parser.add_option('--devicesonly', dest='devicesonly',
            action="store_true", default=False,
            help="Only check for device files. Not components")
        self.parser.add_option('--collector', dest='collector',
            help="Name of specific collector to check (optional)")
        self.parser.add_option('-o', '--file', dest='file',
            help="Output filename")
        self.parser.add_option('--sendevent', dest='sendevent',
            action="store_true", default=False,
            help="Send an event with statistics per collector")

    def run(self):
        if not self.options.file:
            log.critical("You must specify the output file.")
            return

        try:
            outfile = open(self.options.file, 'w')
        except IOError, ex:
            log.critical("Unable to open %s for writing: %s",
                self.options.file, ex)
            return

        if self.options.all:
            log.info("Starting check for missing, stale or orphaned RRD files")
            log.info("Results based on all RRD files defined by data points")
        else:
            log.info("Starting check for missing or stale RRD files")
            log.info("Results based on all RRD files used in graphs")

        if self.options.collector:
            try:
                collectors = [self.dmd.Monitors.Performance._getOb(
                    self.options.collector)]
            except AttributeError:
                log.critical("No collector named %s could be found. Exiting",
                    self.options.collector)
                return
        else:
            collectors = self.dmd.Monitors.Performance.objectValues(
                spec="PerformanceConf")

        collectors = [collectorStats(x.id, getattr(x, 'hostname', x.id)) \
                        for x in collectors]
        self._getExpectedFiles(collectors)

        for collector in collectors:
            if len(collector.expectedFiles) == 0:
                collector.expected = 0
                log.debug("No expected files found for collector %s",
                    collector.id)
                continue

            self._getCollectorFiles(collector)
            if self.options.all:
                for path in sorted(collector.allFiles - collector.expectedFiles):
                    outfile.write("orphaned:%s:%s\n" % (collector.id, path))
                    collector.orphan += 1

            for path in sorted(collector.expectedFiles - collector.staleFiles):
                if path in collector.allFiles:
                    outfile.write("stale:%s:%s\n" % (collector.id, path))
                    collector.stale += 1
                else:
                    outfile.write("missing:%s:%s\n" % (collector.id, path))
                    collector.missing += 1

        outfile.close()
        self.report(collectors)

    def report(self, collectors):
        totalExpectedRRDs = sum(len(x.expectedFiles) for x in collectors)
        totalAllRRDs = sum(len(x.allFiles) for x in collectors)
        totalMissingRRDs = sum(x.missing for x in collectors)
        totalStaleRRDs = sum(x.stale for x in collectors)
        #totalComponentRRDs = sum(x.expectedComponents for x in collectors)
        #totalDeviceRRDs = totalExpectedRRDs - totalComponentRRDs
        header = """
                              On-disk Expected   Missing    Stale
Collector                        RRDs     RRDs      RRDs     RRDs"""
        delimLen = 65
        if self.options.all:
            header += " Orphans"
            delimLen = 75
        print header
        print '-' * delimLen
    
        collectorNames = dict(zip(map(lambda x: x.id, collectors), collectors))
        for name in sorted(collectorNames.keys()):
            collector = collectorNames[name]
            expected = len(collector.expectedFiles)
            all = len(collector.allFiles)
            line = "%-30s %6s   %6s    %6s   %6s" % (
                   name, all, expected, collector.missing, collector.stale)
            if self.options.all:
                line += " %6s" % collector.orphan
            print line
            if self.options.sendevent:
                self._sendCollectorRrdStatsEvent(collector, all, expected, line)

        print '-' * delimLen
        trailer = "%-30s %6s   %6s    %6s   %6s" % (
                   'Total', totalAllRRDs, totalExpectedRRDs,
                   totalMissingRRDs, totalStaleRRDs)
        if self.options.all:
            trailer += " %6s" % sum(x.orphan for x in collectors)
        print trailer

    def _sendCollectorRrdStatsEvent(self, collector, all, expected, stats):
        severity = SEVERITY_ERROR if (collector.missing + collector.stale) > 0 else SEVERITY_CLEAR
        msg = 'Collector RRD statistics: missing=%s stale=%s' (collector.missing, collector.stale)
        ev = dict(device=collector.hostname, component=collector.id,
                  severity=severity, eventClass=Status_Perf,
                  summary=msg, rrdsOnDisk=all, rrdsExpected=expected,
                  rrdsMissing=collector.missing, rrdsStale=collector.stale,
                  rrdsOrphaned=collector.orphan,
        )
        self.dmd.ZenEventManager.sendEvent(ev)

    def _getExpectedFiles(self, collectors):
        rrdFiles = set()
        componentRrdFiles = set()

        if self.options.pathcache and os.path.isfile(CACHE_FILE):
            log.debug("Reading list of expected RRD files from cache...")
            f = open('.rrdcheck.state', 'r')
            rrdFiles = load(f)
            f.close()
        else:
            log.debug("Building list of expected device RRD files..")
            for device in self.dmd.Devices.getSubDevicesGen():
                if not device.monitorDevice(): continue
                rrdFiles.update(self._getRRDPaths(device))
                device._p_deactivate()

            if not self.options.devicesonly:
                log.debug("Building list of expected component RRD files..")
                for component in self._getAllMonitoredComponents():
                    componentRrdFiles.update(self._getRRDPaths(component))
                    component._p_deactivate()

            # Dump the cache in case we want to use it next time.
            f = open('.rrdcheck.state', 'w')
            dump(rrdFiles, f)
            f.close()

        collectorNames = dict(zip(map(lambda x: x.id, collectors), collectors))
        for collectorName, path in rrdFiles:
            collector = collectorNames.get(collectorName, None)
            if collector:
                collector.expectedFiles.add(path)

        for collectorName, path in componentRrdFiles:
            collector = collectorNames.get(collectorName, None)
            if collector:
                collector.expectedComponents += 1
                collector.expectedFiles.add(path)

    def _getRRDPaths(self, ob):
        ob_rrds = set()
        path = ob.fullRRDPath()
        perfServer = ob.getPerformanceServer()
        if not perfServer: return []
        if self.options.all:
            for t in ob.getRRDTemplates():
                for ds in t.datasources():
                    for dp in ds.datapoints():
                        ob_rrds.add((perfServer.id,
                            os.path.join(path, "%s_%s.rrd" % (ds.id, dp.id))))
        else:
            for t in ob.getRRDTemplates():
                for g in t.graphDefs():
                    for cmd in g.getGraphCmds(ob, path):
                        match = rrdMatch(cmd)
                        if match:
                            ob_rrds.add((perfServer.id, match.group(1)))
        transaction.abort()
        return ob_rrds

    def _getAllMonitoredComponents(self):
        for component in self.dmd.Devices.getMonitoredComponents():
            if not component.snmpIgnore():
                yield component

    def _getCollectorFiles(self, collector):
        def parseOutput(output):
            files = set()
            for line in ( l.strip() for l in output.split('\n') if l ):
                files.add(line)
            return files

        log.debug("Checking collector %s (%s) for RRD files",
            collector.id, collector.hostname)

        allCmd = "find %s -name *.rrd" % zenPath('perf', 'Devices')
        staleCmd = "%s -mtime -%s" % (allCmd, self.options.age)

        if collector.hostname == 'localhost':
            allOutput = Popen([allCmd],
                shell=True, stdout=PIPE).communicate()[0]            
            staleOutput = Popen([staleCmd],
                shell=True, stdout=PIPE).communicate()[0]            
        else:
            # Quick check to see if we can SSH to the collector.
            p1 = Popen(["echo", "0"], stdout=PIPE)
            p2 = Popen(["nc", "-w", "4", collector.hostname, "22"],
                stdin=p1.stdout, stdout=PIPE, stderr=PIPE)

            if os.waitpid(p2.pid, 0)[1] != 0:
                log.warn("Unable to SSH to collector %s (%s)", 
                         collector.id, collector.hostname)
                return

            allOutput = Popen(["ssh", collector.hostname, allCmd],
                stdout=PIPE).communicate()[0]
            staleOutput = Popen(["ssh", collector.hostname, staleCmd],
                stdout=PIPE).communicate()[0]

        collector.allFiles = parseOutput(allOutput)
        collector.staleFiles = parseOutput(staleOutput)


if __name__ == '__main__':
    zrc = ZenCheckRRD()
    zrc.run()

