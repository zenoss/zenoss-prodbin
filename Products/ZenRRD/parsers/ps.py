###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, 2010,  Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """ps
Interpret the output from the ps command and provide performance data for
CPU utilization, total RSS and the number of processes that match the
/Process tree definitions.
"""

import re
import logging
log = logging.getLogger("zen.ps")

import Globals
from Products.ZenRRD.CommandParser import CommandParser
from Products.ZenEvents.ZenEventClasses import Status_OSProcess

# Keep track of state between runs
AllPids = {} # (device, processName)
emptySet = set()

class ps(CommandParser):

    def dataForParser(self, context, datapoint):
        id, name, ignoreParams, alertOnRestart, failSeverity = \
            context.getOSProcessConf()
        return dict(processName=name,
                    ignoreParams=ignoreParams,
                    alertOnRestart=alertOnRestart,
                    failSeverity=failSeverity)

    def sendEvent(self, results, **kwargs):
        results.events.append(dict(
                    eventClass=Status_OSProcess,
                    eventGroup='Process',
                    **kwargs))

    def getMatches(self, matchers, procName, cmdAndArgs):
        """
        Get regex matches of processes running on the machine
        """
        matches = []
        for dp, procRegex in matchers.items():
            if dp.data['ignoreParams']:
                name = procName
            else:
                name = cmdAndArgs

            if procRegex.search(name):
                matches.append(dp)
        return matches

    def getProcInfo(self, line):
        """
        Process the non-empyt ps and return back the
        standard info.

        @parameter line: one line of ps output
        @type line: text
        @return: pid, rss, cpu, cmdAndArgs (ie full process name)
        @rtype: tuple
        """
        pid, rss, cpu, cmdAndArgs = line.split(None, 3)
        return pid, rss, cpu, cmdAndArgs

    def groupProcs(self, matchers, output):
        """
        Group processes per datapoint
        """
        dpsToProcs = {}
        for line in output.split('\n')[1:]:
            if not line:
                continue

            try:
                pid, rss, cpu, cmdAndArgs = self.getProcInfo(line)
                log.debug("line '%s' -> pid=%s " \
                              "rss=%s cpu=% cmdAndArgs=%s",
                               pid, rss, cpu, cmdAndArgs)

            except (SystemExit, KeyboardInterrupt): raise
            except:
                log.warn("Unable to parse entry '%s'", line)
                continue

            try:
                procName = cmdAndArgs.split()[0]
                matches = self.getMatches(matchers, procName, cmdAndArgs)

                if not matches:
                    continue

                days = 0
                if cpu.find('-') > -1:
                    days, cpu = cpu.split('-')
                    days = int(days)
                cpu = map(int, cpu.split(':'))
                if len(cpu) == 3:
                    cpu = (days * 24 * 60 * 60 +
                       cpu[0] * 60 * 60 +
                       cpu[1] * 60 +
                       cpu[2])
                elif len(cpu) == 2:
                    cpu = (days * 24 * 60 * 60 +
                       cpu[0] * 60 +
                       cpu[1])

                rss = int(rss)
                pid = int(pid)

                for dp in matches:
                    procInfo = dict(procName=procName,
                       cmdAndArgs=cmdAndArgs, rss=0.0, cpu=0.0,
                       pids=set())
                    procInfo = dpsToProcs.setdefault(dp, procInfo)
                    procInfo['rss'] += rss
                    procInfo['cpu'] += cpu
                    procInfo['pids'].add(pid)

            except (SystemExit, KeyboardInterrupt): raise
            except:
                log.exception("Unable to convert entry data pid=%s " \
                              "rss=%s cpu=% cmdAndArgs=%s",
                               pid, rss, cpu, cmdAndArgs)
                continue
        return dpsToProcs


    def processResults(self, cmd, results):

        # map data points by procesName
        matchers = {}
        for dp in cmd.points:
            matchers[dp] = re.compile(dp.data['processName'])

        dpsToProcs = self.groupProcs(matchers, cmd.result.output)

        # report any processes that are missing, and post perf data
        for dp in cmd.points:
            process = dp.data['processName']
            failSeverity = dp.data['failSeverity']
            procInfo = dpsToProcs.get(dp, None)
            if not procInfo:
                self.sendEvent(results,
                    summary='Process not running: ' + process,
                    component=process,
                    severity=failSeverity)
            else:
                if 'cpu' in dp.id:
                    results.values.append( (dp, procInfo['cpu']) )
                if 'mem' in dp.id:
                    results.values.append( (dp, procInfo['rss']) )
                if 'count' in dp.id:
                    results.values.append( (dp, len(procInfo['pids'])) )

            # Report process changes
            # Note that we can't tell the difference between a
            # reconfiguration from zenhub and process that goes away.
            device = cmd.deviceConfig.device
            before = AllPids.get( (device, process), emptySet)
            after = set()
            if procInfo:
                after = procInfo['pids']

            alertOnRestart = dp.data['alertOnRestart']

            if before != after:
                if len(before) > len(after) and alertOnRestart:
                    pids = ', '.join(map(str, before - after))
                    self.sendEvent(results,
                        summary='Pid(s) %s stopped: %s' % (pids, process),
                        component=process,
                        severity=failSeverity)
                if len(before) == len(after) and alertOnRestart:
                    # process restarted
                    pids = ', '.join(map(str, before - after))
                    self.sendEvent(results,
                        summary='Pid(s) %s restarted: %s' % (pids, process),
                        component=process,
                        severity=failSeverity)
                if len(before) < len(after):
                    if len(before) == 0:
                        self.sendEvent(results,
                            summary='Process running: %s' % process,
                            component=process,
                            severity=0)

            AllPids[device, process] = after
