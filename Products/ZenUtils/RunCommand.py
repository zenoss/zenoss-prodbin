#!/usr/bin/env python
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


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
                           default=60, type="int",
                           help="Kill the process after this many seconds.")
        self.parser.add_option('-n', '--useprefix', action='store_false',
                               dest='useprefix', default=True,
                           help="Prefix the collector name for remote servers")

    def run(self):
        collectors = self._getCollectors()
        if collectors is None:
            return
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

        if collector.id == 'localhost' or not self.options.useprefix:
            remote_command = self.args[0]
        else:
            remote_command = '%s_%s' % (collector.id, self.args[0])

        if collector.hostname == 'localhost':
            collectorCommand = [remote_command]
        else:
            collectorCommand = ['ssh', collector.hostname, remote_command]

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
