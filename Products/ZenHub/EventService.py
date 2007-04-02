from twisted.spread import pb

from Products.ZenEvents.Event import Event
pb.setUnjellyableForClass(Event, Event)

from HubService import HubService

class EventService(HubService):
    
    def remote_sendEvent(self, evt):
        'XMLRPC requests are processed asynchronously in a thread'
        if type(evt) == dict:
            evt = Event(**data)
        return self.zem.sendEvent(evt)

    def remote_sendEvents(self, evts):
        if len(evts) and type(evts[0]) == dict:
            evts = [Event(**e) for e in data] 
        return self.zem.sendEvents(evts)
