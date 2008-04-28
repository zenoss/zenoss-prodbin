from twisted.internet.protocol import ProcessProtocol
from twisted.internet import reactor

import logging
log = logging.getLogger("zen.WmiClient")

import sys

from Products.ZenUtils.Utils import zenPath

class WmiClient(ProcessProtocol):
    "Invoke zenwinmodeler on the device to model it"

    def __init__(self, device, modeler):
        self.device = device
        self.modeler = modeler
        self.timeout = None
        self.timedOut = False
        self.outReceived = sys.stdout.write
        self.errReceived = sys.stderr.write
        self.datacollector = modeler

    def processEnded(self, reason):
        self.datacollector.clientFinished(self)


    def run(self):
        modeler = zenPath('bin', 'zenwinmodeler')
        args = ('run', '-d', self.device.id)
        if '--weblog' in sys.argv:
            args += ('--weblog',)
        reactor.spawnProcess(self, modeler, (modeler,) + args, env=None)

    def getResults(self):
        return []
