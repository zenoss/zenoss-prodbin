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
        if not self.process:
            return
        try:
            self.process.signalProcess(signal.SIGSTOP)
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
        reactor.spawnProcess(self, modeler, (modeler,) + args, env=None)

