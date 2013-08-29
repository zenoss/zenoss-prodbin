##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


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
from Products.ZenModel.OSProcess import OSProcess


# Keep track of state between runs
AllPids = {} # (device, cmdAndArgs)
emptySet = set()


class ps(CommandParser):

    def dataForParser(self, context, datapoint):
        id, alertOnRestart, failSeverity = context.getOSProcessConf()
        return dict(id=id,
                    alertOnRestart=alertOnRestart,
                    failSeverity=failSeverity)

    def sendEvent(self, results, **kwargs):
        results.events.append(dict(
                    eventClass=Status_OSProcess,
                    eventGroup='Process',
                    **kwargs))

    def getProcInfo(self, line):
        """
        Process the non-empyt ps and return back the
        standard info.

        @parameter line: one line of ps output
        @type line: text
        @return: pid, rss, cpu, cmdAndArgs (ie full process name)
        @rtype: tuple
        """
        try:
            pid, rss, cpu, cmdAndArgs = line.split(None, 3)
        except ValueError:
            # Defunct processes look like this (no RSS data)
            # '28835916 00:00:00 <defunct>'
            pid, cpu, cmdAndArgs = line.split(None, 2)
            rss = '0'

        return pid, rss, cpu, cmdAndArgs

    def groupProcs(self, points, compiledRegex, compiledSearchRegex, output, componentId):
        """
        Group processes per datapoint
        """
        dpsToProcs = {}

        # for every line found found from issuing the ps statement on the remote box
        for line in output.split('\n')[1:]:
            if not line:
                continue

            try:
                pid, rss, cpu, cmdAndArgs = self.getProcInfo(line)
                log.debug("line '%s' -> pid=%s " \
                              "rss=%s cpu=%s cmdAndArgs=%s",
                               line, pid, rss, cpu, cmdAndArgs)

            except Exception:
                log.warn("Unable to parse entry '%s'", line)
                continue

            try:
                matches = []
                
                if OSProcess.matchRegex(compiledRegex, compiledSearchRegex, cmdAndArgs) and \
                   OSProcess.matchNameCaptureGroups(compiledRegex, cmdAndArgs, componentId):
                    matches.extend(points)

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

                # cpu is ticks per second per cpu, tick is a centisecond, we
                # want seconds
                cpu *= 100

                rss = int(rss)
                pid = int(pid)

                for dp in matches:
                    # add values
                    procInfo = dict(cmdAndArgs=cmdAndArgs, rss=0.0, cpu=0.0, pids={})
                    procInfo = dpsToProcs.setdefault(dp, procInfo)
                    procInfo['rss'] += rss
                    procInfo['cpu'] += cpu
                    procInfo['pids'][pid] = cmdAndArgs
            
            except Exception:
                log.exception("Unable to convert entry data pid=%s " \
                              "rss=%s cpu=%s cmdAndArgs=%s",
                               pid, rss, cpu, cmdAndArgs)
                continue

        return dpsToProcs


    def processResults(self, cmd, results):
        dpsToProcs = self.groupProcs(cmd.points, re.compile(cmd.regex), re.compile(cmd.excludeRegex), cmd.result.output, cmd.componentId)

        # report any processes that are missing, and post perf data
        for dp in cmd.points:
            failSeverity = dp.data['failSeverity']
            procInfo = dpsToProcs.get(dp, None)
            
            if not procInfo:
                self.sendEvent(results,
                    summary='Process not running: ' + dp.data["id"],
                    component=dp.data["id"],
                    severity=failSeverity)
                log.debug("device:%s, command: %s, procInfo: %r, failSeverity: %r, process: %s, dp: %r",
                            cmd.deviceConfig.device,
                            cmd.command,
                            procInfo,
                            failSeverity,
                            dp.data["id"],
                            dp)
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
        beforePidsAndProcesses = AllPids.get( (device, dp.data["id"]), {})
        
        afterPidsProcesses = {}
        if procInfo:
            afterPidsProcesses = procInfo['pids']

        alertOnRestart = dp.data['alertOnRestart']
        
        beforeCmdAndArgs = []
        for pidKey in beforePidsAndProcesses.keys():
            beforeCmdAndArgs.append(beforePidsAndProcesses[pidKey])

        restartedCmdAndArgsSet = set()
        runningPidsSet = set()
        for pidKey in afterPidsProcesses.keys():
            # pid is NOT in the beforePidsAndProcesses however the CmdAndArgs IS in beforePidsAndProcesses = process restarted
            if pidKey not in beforePidsAndProcesses.keys() and \
               afterPidsProcesses[pidKey] in beforeCmdAndArgs and \
               alertOnRestart:
                restartedCmdAndArgsSet.add(afterPidsProcesses[pidKey])
                self.sendEvent(results,
                    summary='Pid %s restarted: %s' % (pidKey, afterPidsProcesses[pidKey]),
                    component=afterPidsProcesses[pidKey],
                    severity=failSeverity)
            # same pid = process is still running
            # different pid, different process = new process running
            else:
                runningPidsSet.add(pidKey)
                self.sendEvent(results,
                    summary='Pid %s running: %s' % (pidKey, afterPidsProcesses[pidKey]),
                    component=afterPidsProcesses[pidKey],
                    severity=0)

        beforePidsSet = set(beforePidsAndProcesses.keys())

        restartedPidsSet = set()
        for pidKey in beforePidsAndProcesses.keys():
            if beforePidsAndProcesses[pidKey] in restartedCmdAndArgsSet:
                restartedPidsSet.add(pidKey)

        # stoppedPids = the pids that were running ... that are neither still running nor have been restarted
        stoppedPidsSet = beforePidsSet - runningPidsSet - restartedPidsSet
        for pidKey in stoppedPidsSet:
            if alertOnRestart:
                self.sendEvent(results,
                    summary='Pid %s stopped: %s' % (pidKey, beforePidsAndProcesses[pidKey]),
                    component=beforePidsAndProcesses[pidKey],
                    severity=failSeverity)
        '''
        print " ##### Running  : %s" % afterPidsProcesses
        print " ##### Restarted: %s" % beforePidsAndProcesses
        print " ##### Stopped  : %s" % beforePidsAndProcesses
        '''

        AllPids[device, dp.data["id"]] = afterPidsProcesses
