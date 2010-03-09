#!/usr/bin/env python
#############################################################################
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#############################################################################

import os
import re
import sys
from pickle import dump, load
from subprocess import Popen, PIPE

import Globals
import transaction
from Products.ZenUtils.Utils import zenPath
from Products.ZenUtils.ZenScriptBase import ZenScriptBase

import logging
log = logging.getLogger('zen.checkRRD')

CACHE_FILE = zenPath('var', 'zencheckrrd.cache')
rrdMatch = re.compile('DEF:[^=]+=([^:]+)').match

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
        self.parser.add_option('--file', dest='file',
            help="Output filename")


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

        expectedByCollector = self._getExpectedFiles()
        missingOrStale_count = 0
        orphan_count = 0
        total_count = 0

        for collector in collectors:
            collector_missingOrStale = 0
            collector_orphan = 0

            expectedFiles = expectedByCollector.get(collector.id, None)
            if not expectedFiles:
                log.info("No expected files found for collector %s",
                    collector.id)
                continue

            total_count += len(expectedFiles)

            collectorFiles = self._getCollectorFiles(collector)
            if self.options.all:
                for path in sorted(collectorFiles - expectedFiles):
                    outfile.write("orphaned:%s:%s\n" % (collector.id, path))
                    collector_orphan += 1

                log.info("Found %s orphaned RRD files on %s",
                    collector_orphan, collector.id)
                orphan_count += collector_orphan

            for path in sorted(expectedFiles - collectorFiles):
                outfile.write("missingOrStale:%s:%s\n" % (collector.id, path))
                collector_missingOrStale += 1

            log.info("Found %s missing or stale files on %s",
                collector_missingOrStale, collector.id)

            missingOrStale_count += collector_missingOrStale

        outfile.close()

        log.info("%s out of %s RRD files are missing or stale",
            missingOrStale_count, total_count)

        if self.options.all:
            log.info("%s orphaned RRD files", orphan_count)


    def _getExpectedFiles(self):
        rrdFiles = set()

        if self.options.pathcache and os.path.isfile(CACHE_FILE):
            log.info("Reading list of expected RRD files from cache..")
            f = open('.rrdcheck.state', 'r')
            rrdFiles = load(f)
            f.close()
            log.info("%s expected RRD files in the cache", len(rrdFiles))
        else:
            log.info("Building list of expected device RRD files..")
            for device in self.dmd.Devices.getSubDevicesGen():
                if not device.monitorDevice(): continue
                rrdFiles.update(self._getRRDPaths(device))
                device._p_deactivate()

            device_rrd_count = len(rrdFiles)
            log.info("%s expected device RRD files", device_rrd_count)

            if not self.options.devicesonly:
                log.info("Building list of expected component RRD files..")
                for component in self._getAllMonitoredComponents():
                    rrdFiles.update(self._getRRDPaths(component))
                    component._p_deactivate()

                log.info("%s expected component RRD files",
                    (len(rrdFiles) - device_rrd_count))

            # Dump the cache in case we want to use it next time.
            f = open('.rrdcheck.state', 'w')
            dump(rrdFiles, f)
            f.close()

        expectedFiles = {}
        for collector, path in rrdFiles:
            if collector not in expectedFiles:
                expectedFiles[collector] = set()
            expectedFiles[collector].add(path)

        return expectedFiles


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
        brains = self.dmd.Devices.componentSearch({'monitored': True})
        for component in ( b.getObject() for b in brains ):
            if not component.snmpIgnore():
                yield component


    def _getCollectorFiles(self, collector):
        host = getattr(collector, 'hostname', collector.id)
        log.info("Checking collector %s (%s) for fresh files",
            collector.id, host)

        if host == 'localhost':
            output = Popen(["find %s -name *.rrd -mtime -%s" % (
                zenPath('perf', 'Devices'), self.options.age)],
                shell=True, stdout=PIPE).communicate()[0]            
        else:
            # Quick check to see if we can SSH to the collector.
            p1 = Popen(["echo", "0"], stdout=PIPE)
            p2 = Popen(["nc", "-w", "4", host, "22"],
                stdin=p1.stdout, stdout=PIPE, stderr=PIPE)

            if os.waitpid(p2.pid, 0)[1] != 0:
                log.warn("Unable to SSH to collector %s (%s)", collector.id, host)

            output = Popen(["ssh", host,
                "find $ZENHOME -name *.rrd -mtime -%s" % self.options.age],
                stdout=PIPE).communicate()[0]

        files = set()
        for line in ( l.strip() for l in output.split('\n') if l ):
            files.add(line)

        log.info("Found %s total RRD files on collector %s",
            len(files), collector.id)
        return files


if __name__ == '__main__':
    zrc = ZenCheckRRD()
    zrc.run()
