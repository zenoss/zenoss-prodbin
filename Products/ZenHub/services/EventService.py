from twisted.spread import pb

from Products.ZenEvents.Event import Event
pb.setUnjellyableForClass(Event, Event)

from HubService import HubService

class EventService(HubService):

    def remote_sendEvent(self, evt):
        'XMLRPC requests are processed asynchronously in a thread'
        return self.zem.sendEvent(evt)

    def remote_sendEvents(self, evts):
        return self.zem.sendEvents(evts)

    def remote_getDevicePingIssues(self, *args, **kwargs):
        return self.zem.getDevicePingIssues(*args, **kwargs)

