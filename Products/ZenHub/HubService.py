
from twisted.spread import pb

class HubService(pb.Referenceable):

    def __init__(self, dmd):
        self.dmd = dmd
        self.zem = dmd.ZenEventManager


    def getName(self): 
        """Return the service name
        """
        return self.__class__.__name__
