###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import Globals
from Products.ZenRRD.CommandParser import CommandParser
from Products.ZenEvents.ZenEventClasses import Status_OSProcess

AllPids = {}

emptySet = set()

class ps(CommandParser):

    def dataForParser(self, context, datapoint):
        id, name, ignoreParams, alertOnRestart, failSeverity = \
            context.getOSProcessConf()
        return dict(processName=name,
                    ignoreParams=ignoreParams,
                    alertOnRestart=alertOnRestart,
                    failSeverity=failSeverity)
    
    def processResults(self, cmd, results):

        # map data points by procesName
        dps = {}
        for dp in cmd.points:
            dps.setdefault(dp.data['processName'], []).append(dp)

        # group running processes by name (with and without args)
        running = {}
        for line in cmd.result.output.split('\n')[1:]:
            if not line: continue
            try:
                pid, rss, cpu, args = line.split(None, 3)
                days = 0
                if cpu.find('-') > -1:
                    days, cpu = cpu.split('-')
                    days = int(days)
                cpu = map(int, cpu.split(':'))
                cpu = (days * 24 * 60 * 60 +
                       cpu[0] * 60 * 60 +
                       cpu[1] * 60 +
                       cpu[2])
                rss = int(rss)
                pid = int(pid)
                lst = running.setdefault(args, [])
                lst.append( (pid, rss, cpu) )
                lst = running.setdefault(args.split()[0], [])
                lst.append( (pid, rss, cpu) )
            except ValueError:
                continue
        # report any processes that are missing, and post perf data
        for process, points in dps.items():
            match = running.get(process, [])
            if not match:
                results.events.append(dict(
                    summary='Process not running: ' + process,
                    eventClass=Status_OSProcess,
                    eventGroup='Process',
                    component=process,
                    severity=points[0].data['failSeverity']
                    ))
            else:
                totalRss = sum([rss for pid, rss, cpu in match])
                totalCpu = sum([cpu for pid, rss, cpu in match])
                for dp in points:
                    if 'cpu' in dp.id:
                        results.values.append( (dp, totalCpu) )
                    if 'mem' in dp.id:
                        results.values.append( (dp, totalRss) )
                    if 'count' in dp.id:
                        results.values.append( (dp, len(match)) )

            # report process changes
            device = cmd.deviceConfig.device
            before = AllPids.get( (device, process), emptySet)
            after = set([pid for pid, rss, cpu in match])
            alertOnRestart = points[0].data['alertOnRestart']
            if before != after:
                if len(before) > len(after) and alertOnRestart:
                    pids = ', '.join(map(str, before - after))
                    results.events.append(dict(
                        summary='Pid(s) %s stopped: %s' % (pids, process),
                        eventClass=Status_OSProcess,
                        eventGroup='Process',
                        component=process,
                        severity=points[0].data['failSeverity']
                        ))
                if len(before) == len(after) and alertOnRestart:
                    # process restarted
                    pids = ', '.join(map(str, before - after))
                    results.events.append(dict(
                        summary='Pid(s) %s restarted: %s' % (pids, process),
                        eventClass=Status_OSProcess,
                        eventGroup='Process',
                        component=process,
                        severity=points[0].data['failSeverity']
                        ))
                if len(before) < len(after):
                    if len(before) == 0:
                        results.events.append(dict(
                            summary='Process running: %s' % process,
                            eventClass=Status_OSProcess,
                            eventGroup='Process',
                            component=process,
                            severity=0
                            ))

            AllPids[device, process] = after
