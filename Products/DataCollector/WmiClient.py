###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from twisted.internet.protocol import ProcessProtocol
from twisted.internet import reactor
from twisted.internet import error

import sys

from Products.ZenUtils.Utils import zenPath
from BaseClient import BaseClient

class WmiClient(BaseClient, ProcessProtocol):
    "Invoke zenwinmodeler on the device to model it"

    def __init__(self, device, datacollector):
        BaseClient.__init__(self, device, datacollector)
        self.process = None
        self.outReceived = sys.stdout.write
        self.errReceived = sys.stderr.write

    def processEnded(self, reason):
        if self.datacollector:
            self.datacollector.clientFinished(self)
        self.process = None

    def stop(self):
        import signal
        if not self.process:
            return
        try:
            self.process.signalProcess(signal.SIGKILL)
        except error.ProcessExitedAlready:
            pass
        try:
            self.process.loseConnection()
        except Exception:
            pass
        self.process = None


    def run(self):
        modeler = zenPath('bin', 'zenwinmodeler')
        args = ('run', '-d', self.device.id)
        if '--weblog' in sys.argv:
            args += ('--weblog',)
        self.process = reactor.spawnProcess(self, modeler, (modeler,) + args, env=None)

