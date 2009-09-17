import zope.interface
from interfaces import IEventManagerProxy

class EventManagerProxy(object):
    """
    An adapter holding several methods useful for interacting with a Zenoss
    event manager.
    """
    zope.interface.implements(IEventManagerProxy)

    def __init__(self, view):
        self.context = view.context
        self.request = view.request

    @property
    def is_history(self):
        # If we're actually loading event console, False
        if 'viewEvents' in self.request.getURL():
            return False
        # If we're loading history page or a request from the history page,
        # True, else False
        return ('viewHistoryEvents' in self.request.getURL() or
                'viewHistoryEvents' in self.request['HTTP_REFERER'])

    def event_manager(self, forceHistory=False):
        evmgr = getattr(self, '_evmgr', None)
        if not evmgr:
            if forceHistory or self.is_history:
                evmgr = self.context.dmd.ZenEventHistory
            else:
                evmgr = self.context.dmd.ZenEventManager
            self._evmgr = evmgr
        return evmgr

    def _get_device_url(self, devname):
        dev = self.context.dmd.Devices.findDevice(devname)
        if dev:
            return dev.absolute_url_path()

    def _get_component_url(self, dev, comp):
        comps = self.context.dmd.searchComponents(dev, comp)
        if comps:
            return comps[0].absolute_url_path()

    def _get_eventClass_url(self, evclass):
        return '/zport/dmd/Events' + evclass

    def extract_data_from_zevent(self, zevent, fields):
        data = {}
        for field in fields:
            value = getattr(zevent, field)
            _shortvalue = str(value) or ''
            if field == 'prodState':
                value = self.context.dmd.convertProdState(value)
            elif field == 'eventState':
                value = self.event_manager().eventStateConversions[value][0]
            elif 'Time' in field:
                value = value.rsplit('.')[0].replace('/', '-')
            elif field == 'eventClass':
                data['eventClass_url'] = self._get_eventClass_url(value)
            elif field == 'device':
                url = self._get_device_url(value)
                if url: data['device_url'] = url
            elif field == 'component':
                dev = getattr(zevent, 'device', None)
                if dev:
                    url = self._get_component_url(dev, value)
                    if url: data['component_url'] = url
            else:
                value = _shortvalue
            data[field] = value
        data['evid'] = zevent.evid
        data['id'] = zevent.evid
        return data

