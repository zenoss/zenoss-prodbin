##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009-2013, all rights reserved.
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
from Products.ZenEvents import Event
from Products.ZenEvents.ZenEventClasses import Status_OSProcess
from Products.ZenModel.OSProcessMatcher import OSProcessDataMatcher
from Products.ZenModel.OSProcessState import determineProcessState


# Keep track of state between runs
# (device, cmdAndArgs)
Globals.MostRecentMonitoredTimePids = getattr(Globals, "MostRecentMonitoredTimePids", {})

def parseCpuTime(cputime):
    """
    Parse the cputime field of a process (output from the ps command).

    @return: number of seconds
    @rtype: int
    """
    days = 0
    if cputime.find('-') > -1:
        days, cputime = cputime.split('-')
        days = float(days)
    cputime = map(float, cputime.split(':'))
    if len(cputime) == 3:
        cputime = (days * 24 * 60 * 60 +
           cputime[0] * 60 * 60 +
           cputime[1] * 60 +
           cputime[2])
    elif len(cputime) == 2:
        cputime = (days * 24 * 60 * 60 +
           cputime[0] * 60 +
           cputime[1])
    return int(round(cputime))

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
        Process the non-empty ps and return back the
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

    def _extractProcessMetrics(self, line):
        if line:
            try:
                pid, rss, cpu, cmdAndArgs = self.getProcInfo(line)

                # ----------------------------------------------------------
                # WARNING! Do not modify this debug line at all!
                # The process class interactive testing UI depends on it!
                # (yeah, yeah... technical debt... we know)
                # ----------------------------------------------------------
                log.debug("line '%s' -> pid=%s rss=%s cpu=%s cmdAndArgs=%s",
                          line, pid, rss, cpu, cmdAndArgs)
                # ----------------------------------------------------------

                return int(pid), int(rss), parseCpuTime(cpu), cmdAndArgs
            except:
                log.warn("Unable to parse entry '%s'", line)

    def _combineProcessMetrics(self, metrics):
        combinedPids = {}
        combinedRss = 0.0
        combinedCpu = 0.0
        for pid, rss, cpu, cmdAndArgs in metrics:
            combinedPids[pid] = cmdAndArgs
            combinedRss += rss
            combinedCpu += cpu
        return combinedPids, combinedRss, combinedCpu

    def processResults(self, cmd, results):
        matcher = OSProcessDataMatcher(
            includeRegex   = cmd.includeRegex,
            excludeRegex   = cmd.excludeRegex,
            replaceRegex   = cmd.replaceRegex,
            replacement    = cmd.replacement,
            primaryUrlPath = cmd.primaryUrlPath,
            generatedId    = cmd.generatedId)

        def matches(processMetrics):
            pid, rss, cpu, cmdAndArgs = processMetrics
            return matcher.matches(cmdAndArgs)

        lines = cmd.result.output.splitlines()[1:]
        metrics = map(self._extractProcessMetrics, lines)
        matchingMetrics = filter(matches, metrics)
        pids, rss, cpu = self._combineProcessMetrics(matchingMetrics)

        processSet = cmd.displayName

        # report any processes that are missing, and post perf data
        for dp in cmd.points:
            # cmd.points = list of tuples ... each tuple contains one of the following:
            #    dictionary, count
            #    dictionary, cpu
            #    dictionary, mem        
            if pids:
                if 'cpu' in dp.id:
                    results.values.append( (dp, cpu) )
                if 'mem' in dp.id:
                    results.values.append( (dp, rss) )
                if 'count'in dp.id:
                    results.values.append( (dp, len(pids)) )
            else:
                failSeverity = dp.data['failSeverity']
                # alert on missing (the process set contains 0 processes...)
                summary = 'Process set contains 0 running processes: %s' % processSet
                message = "%s\n   Using regex \'%s\' \n   All Processes have stopped since the last model occurred. Last Modification time (%s)" \
                            % (summary, cmd.includeRegex, cmd.deviceConfig.lastmodeltime)
                self.sendEvent(results,
                    device=cmd.deviceConfig.device,
                    summary=summary,
                    message=message,
                    component=processSet,
                    eventKey=cmd.generatedId,
                    severity=failSeverity)
                log.warning("(%s) %s" % (cmd.deviceConfig.device, message))

        # Report process changes
        # Note that we can't tell the difference between a
        # reconfiguration from zenhub and process that goes away.
        device = cmd.deviceConfig.device

        # Retrieve the current processes and corresponding pids
        afterPidsProcesses = {}
        if pids:
            afterPidsProcesses = pids
        afterPids = afterPidsProcesses.keys()
        afterProcessSetPIDs = {}
        afterProcessSetPIDs[processSet] = afterPids

        # Globals.MostRecentMonitoredTimePids is a global that simply keeps the most recent data ... used to retrieve the "before" at monitoring time
        beforePidsProcesses = Globals.MostRecentMonitoredTimePids.get(processSet, None)
        
        # the first time this runs ... there is no "before"
        # this occurs when beforePidsProcesses is an empty dict
        # we need to save off the current processes and continue til the next monitoring time when "before" and "after" will be present
        if beforePidsProcesses is None:
            log.debug("No existing 'before' process information for process set: %s ... skipping" % processSet)
            Globals.MostRecentMonitoredTimePids[processSet] = afterPidsProcesses
            return
        
        beforePids = beforePidsProcesses.keys()
        beforeProcessSetPIDs = {}
        beforeProcessSetPIDs[processSet] = beforePids

        processState = determineProcessState(beforeProcessSetPIDs, afterProcessSetPIDs)
        (deadPids, restartedPids, newPids) = processState

        # only if configured to alert on restarts...
        alertOnRestart = dp.data['alertOnRestart']
        if alertOnRestart and restartedPids:
            droppedPids = []
            for pid in beforeProcessSetPIDs[processSet]:
                if pid not in afterProcessSetPIDs[processSet]:
                    droppedPids.append(pid)
            summary = 'Process(es) restarted in process set: %s' % processSet
            message = '%s\n Using regex \'%s\' Discarded dead pid(s) %s Using new pid(s) %s'\
                % (summary, cmd.includeRegex, droppedPids, afterProcessSetPIDs[processSet])
            self.sendEvent(results,
                device=cmd.deviceConfig.device,
                summary=summary,
                message=message,
                component=processSet,
                eventKey=cmd.generatedId+"_restarted",
                severity=cmd.severity)
            log.info("(%s) %s" % (cmd.deviceConfig.device, message))

        # report alive processes
        for alivePid in afterProcessSetPIDs[processSet]:
            if alivePid in restartedPids:
                continue
            summary = "Process up: %s" % processSet
            message = '%s\n Using regex \'%s\' with pid\'s %s ' % (summary, cmd.includeRegex, alivePid)
            self.sendEvent(results,
                device=cmd.deviceConfig.device,
                summary=summary,
                message=message,
                component=processSet,
                eventKey=cmd.generatedId,
                severity=Event.Clear)
            log.debug("(%s) %s" % (cmd.deviceConfig.device, message))

        for newPid in newPids:
            log.debug("found new process: %s (pid: %d) on %s" % (afterPidsProcesses[newPid], newPid, cmd.deviceConfig.device))

        Globals.MostRecentMonitoredTimePids[processSet] = afterPidsProcesses
