from sets import Set

class Procrastinate:
    "A class to delay executing a change to a device"
    
    def __init__(self, cback):
        self.cback = cback
        self.devices = Set()
        self.timer = None

    def clear(self):
        self.devices = Set()

    def doLater(self, device = None):
        if self.timer and not self.timer.called:
            self.timer.cancel()
        self.devices.add(device)
        from twisted.internet import reactor
        self.timer = reactor.callLater(5, self._doNow)


    def _doNow(self, *unused):
        if self.devices:
            device = self.devices.pop()
            self.cback(device).addBoth(self._doNow)


