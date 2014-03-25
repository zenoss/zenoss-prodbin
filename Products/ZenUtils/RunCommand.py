#!/usr/bin/env python
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010-2014, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """RunCommand
Run an event command on the serviced host server.

  Example usage:

dcsh --pool=POOL_ID 'zencommand run'

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


class PoolStats:
    def __init__(self, id):
        self.id = id
        self.succeeded = False
        self.stdout = ''
        self.stderr = ''


class RunCommand(ZenScriptBase):
    def __init__(self):
        ZenScriptBase.__init__(self, connect=True)

    def buildOptions(self):
        ZenScriptBase.buildOptions(self)
        self.parser.add_option('--pool', dest='poolId', default='default', metavar='POOL_ID',
            help="Name of specific resource pool on which to run the command")
        self.parser.add_option('--timeout', dest='timeout',
                           default=60, type="int",
                           help="Kill the process after this many seconds.")

    def run(self):
        pool = PoolStats(self.options.poolId)
        self._runCommandOnPool(pool)
        self.report(pool)

    def report(self, pool):
        header = """
Pool=%s            StdOut/Stderr""" % pool.id
        delimLen = 65
        print header
        print '-' * delimLen
    
        print "%s %s" % (pool.stdout, pool.stderr)
        print '-' * delimLen

    def _runCommandOnPool(self, pool):
        def killTimedOutProc(signum, frame):
            log.error("Killing process id %s ...", proc.pid)
            try:
                os.kill(proc.pid, signal.SIGKILL)
            except OSError:
                pass

        remoteCommand = self.args[0]

        # TODO: use pool.id
        poolCommand = ['servicedshell', remoteCommand]

        poolCommand = ' '.join(poolCommand)
        log.debug("Running command '%s' on pool %s", poolCommand, pool.id)
        proc = Popen(poolCommand, stdout=PIPE, stderr=PIPE, shell=True)
        signal.signal(signal.SIGALRM, killTimedOutProc)
        signal.alarm(self.options.timeout)
        pool.stdout, pool.stderr = proc.communicate()
        proc.wait()
        signal.alarm(0) # Disable the alarm


if __name__ == '__main__':
    zrc = RunCommand()
    zrc.run()
