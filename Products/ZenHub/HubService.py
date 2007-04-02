
from twisted.spread import pb

class HubService(pb.Referenceable):

    def __init__(self, dmd, instance = None):
        self.dmd = dmd
        self.zem = dmd.ZenEventManager
        self.instance = instance

