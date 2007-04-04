from HubService import HubService
from twisted.internet import reactor
from twisted.spread import pb
import time

class Beat(HubService):

    def __init__(self, dmd, instance):
        HubService.__init__(self, dmd, instance)
        self.beat()

    def beat(self):
        secs = time.time()
        for listener in self.listeners:
            try:
                d = listener.callRemote('beat', secs)
                d.addErrback(self.error, listener)
            except pb.DeadReferenceError, ex:
                self.error(ex, listener)
        reactor.callLater(1, self.beat)

    def error(self, reason, listener):
        try:
            self.listeners.remove(listener)
        except ValueError:
            pass
        
