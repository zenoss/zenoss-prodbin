
from twisted.spread import pb

class HubService(pb.Referenceable):

    def __init__(self, dmd, instance):
        self.dmd = dmd
        self.zem = dmd.ZenEventManager
        self.instance = instance
        self.listeners = []

    def addListener(self, remote):
        self.listeners.append(remote)
