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

__doc__ = """RunCommand
Run an event command on the local device or on the remote collector.
Assumes that SSH keys have been set up to all remote collectors.

  Example usage:

dcsh -collector=xxx 'zencommand run'

  The actual command to run *MUST* be in quotes!
"""

import logging
log = logging.getLogger('zen.runCommand')

import os
from subprocess import Popen, PIPE
import StringIO
import signal

import Globals
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.ZenUtils.Utils import zenPath


class collectorStats:
    def __init__(self, id, hostname):
        self.id = id
        self.hostname = hostname
        self.succeeded = False
        self.stdout = ''
        self.stderr = ''


class RunCommand(ZenScriptBase):
    def __init__(self):
        ZenScriptBase.__init__(self, connect=True)

    def buildOptions(self):
        ZenScriptBase.buildOptions(self)
        self.parser.add_option('--collector', dest='collector',
            help="Name of specific collector on which to run the command")
        self.parser.add_option('--timeout', dest='timeout',
                           default=60,
                           help="Kill the process after this many seconds.")
        self.parser.add_option('-n', '--useprefix', action='store_false',
                               dest='useprefix', default=True,
                           help="Prefix the collector name for remote servers")

    def run(self):
        collectors = self._getCollectors()
        for collector in collectors:
            self._runCommandOnCollector(collector)
        self.report(collectors)

    def _getCollectors(self):
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

        return [collectorStats(x.id, getattr(x, 'hostname', x.id)) \
                        for x in collectors]

    def report(self, collectors):
        header = """
Collector       StdOut/Stderr"""
        delimLen = 65
        print header
        print '-' * delimLen
    
        collectorNames = dict(zip(map(lambda x: x.id, collectors), collectors))
        for name in sorted(collectorNames.keys()):
            collector = collectorNames[name]
            print "%s     %s %s" % (name, collector.stdout, collector.stderr)
            print '-' * delimLen

    def _runCommandOnCollector(self, collector):
        def killTimedOutProc(signum, frame):
            log.error("Killing process id %s ...", proc.pid)
            try:
                os.kill(proc.pid, signal.SIGKILL)
            except OSError:
                pass

        if collector.hostname == 'localhost':
            collectorCommand = self.args
        else:
            # Quick check to see if we can SSH to the collector.
            #p1 = Popen(["echo", "0"], stdout=PIPE)
            #p2 = Popen(["nc", "-w", "4", collector.hostname, "22"],
            #    stdin=p1.stdout, stdout=PIPE, stderr=PIPE)

            #if os.waitpid(p2.pid, 0)[1] != 0:
            #    log.warn("Unable to SSH to collector %s (%s)", 
            #             collector.id, collector.hostname)
            #    return

            cmd = self.args[0]
            if self.options.useprefix:
                cmd = '%s_%s' % (collector.id, cmd)
            collectorCommand = ['ssh', collector.hostname, cmd]

        collectorCommand = ' '.join(collectorCommand)
        log.debug("Runing command '%s' on collector %s (%s)",
                  collectorCommand, collector.id, collector.hostname)
        proc = Popen(collectorCommand, stdout=PIPE, stderr=PIPE, shell=True)
        signal.signal(signal.SIGALRM, killTimedOutProc)
        signal.alarm(self.options.timeout)
        collector.stdout, collector.stderr = proc.communicate()
        proc.wait()
        signal.alarm(0) # Disable the alarm


if __name__ == '__main__':
    zrc = RunCommand()
    zrc.run()
