from zope.event import notify
from zope.interface import implements
from zope.component import adapts
from Products.ZenUI3.utils.json import json, unjson
from Products.Zuul.utils import resolve_context
from Products.Zuul.facades import ZuulFacade
from Products.Zuul.interfaces import *

class EventEvent(object):
    implements(IEventEvent)
    evid = None
    manager = None
    def __init__(self, evid, manager=None):
        self.evid = evid
        self.manager = manager


class EventStateChanged(EventEvent):
    implements(IEventStateChanged)
    fromState = None
    toState = None
    def __init__(self, evid, manager, fromState, toState):
        super(EventStateChanged, self).__init__(evid, manager)
        self.fromState = fromState
        self.toState = toState


class EventAcknowledged(EventStateChanged):
    implements(IEventAcknowledged)
    def __init__(self, evid, manager, fromState=0, toState=1):
        super(EventAcknowledged, self).__init__(
                evid, manager, fromState, toState)


class EventUnacknowledged(EventStateChanged):
    implements(IEventUnacknowledged)
    def __init__(self, evid, manager, fromState=1, toState=0):
        super(EventUnacknowledged, self).__init__(
                evid, manager, fromState, toState)


class EventAdded(EventEvent):
    implements(IEventAdded)


class EventReopened(EventAdded):
    implements(IEventReopened)


class EventClosed(EventEvent):
    implements(IEventClosed)


class EventInfo(object):
    implements(IEventInfo)
    adapts(IEventEntity)
    
    def __init__(self, event):
        self._event = event

    @property
    def severity(self):
        return self._event.severity
        
    @property
    def device(self):
        return self._event.device

    @property
    def component(self):
        return self._event.component

    @property
    def eventClass(self):
        return self._event.eventClass

    @property
    def summary(self):
        return self._event.summary

class EventFacade(ZuulFacade):
    implements(IEventFacade)

    def _is_history(self, request=None):
        if request is None:
            # We have no idea, so let's go with ZenEventManager
            return False
        # If we're actually loading event console, False
        if 'viewEvents' in request.getURL():
            return False
        # If we're loading history page or a request from the history page,
        # True, else False
        return ('viewHistoryEvents' in request.getURL() or
                'viewHistoryEvents' in request['HTTP_REFERER'])

    def _event_manager(self, history=False):
        if history or self._is_history():
            return self._dmd.ZenEventHistory
        else:
            return self._dmd.ZenEventManager

    def _get_device_url(self, devname):
        dev = self._dmd.Devices.findDevice(devname)
        if dev:
            return dev.absolute_url_path()

    def _get_component_url(self, dev, comp):
        comps = self._dmd.searchComponents(dev, comp)
        if comps:
            return comps[0].absolute_url_path()

    def _get_eventClass_url(self, evclass):
        return '/zport/dmd/Events' + evclass

    def _extract_data_from_zevent(self, zevent, fields):
        data = {}
        for field in fields:
            value = getattr(zevent, field)
            _shortvalue = str(value) or ''
            if field == 'prodState':
                value = self._dmd.convertProdState(value)
            elif field == 'eventState':
                value = self._event_manager().eventStateConversions[value][0]
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

    def log(self, evid, message, history=False):
        zem = self._event_manager(history)
        zem.manage_addLogMessage(evid, message)

    def detail(self, evid, history=False):
        zem = self._event_manager(history)
        details = zem.getEventDetail(evid)
        fields = dict(details.getEventFields())
        event = fields.copy()
        properties = fields.items() + dict(details._details).items()
        properties = [{'key':key,'value':value} for key, value in properties]
        event['properties'] = properties
        event['log'] = details._logs
        for f in ('device', 'component', 'eventClass'):
            func = getattr(self, '_get_%s_url' % f)
            if f=='component':
                args = event['device'], event['component']
            else:
                args = [event[f]]
            url = func(*args)
            if url:
                event[f+'_url'] = url
        return event

    def fields(self, context=None):
        if context is None:
            context = self._dmd.Events
        context = resolve_context(context)
        zem = self._event_manager()
        if hasattr(context, 'getResultFields'):
          fs = context.getResultFields()
        else:
          # Use default result fields
          if hasattr(context, 'event_key'):
              base = context
          else:
              base = self._dmd.Events.primaryAq()
          fs = zem.lookupManagedEntityResultFields(base.event_key)
        return fs

    def query(self, limit=0, start=0, sort='lastTime', dir='DESC',
              filters=None):
        context = self._dmd.Events
        if isinstance(filters, basestring): filters = unjson(filters)
        zem = self._event_manager()

        fields = self.fields()

        start = max(start, 0)
        limit = max(limit, 0)

        if not filters:
            filters = {}

        args = dict(
            offset=start,
            rows=limit,
            resultFields=fields,
            getTotalCount=True,
            sort=sort,
            orderby="%s %s, lastTime DESC" % (sort, dir),
            filters=filters
        )
        events, total = zem.getEventListME(context, **args)
        data = [self._extract_data_from_zevent(ev, fields) for ev in events]
        return {
            'total': total,
            'events': events,
            'data': data
        }

    def create(self, summary, severity, device=None, component=None, **kwargs):
        zem = self._event_manager()
        if isinstance(severity, basestring):
            sevs = ['Clear', 'Debug', 'Info', 'Warning', 'Error', 'Critical']
            severity = sevs.index(severity)
        args = dict(summary=summary, severity=severity)
        if device: args['device'] = device
        if component: args['component'] = component
        args.update(kwargs)
        evid = zem.manage_addEvent(args)
        if evid:
            notify(EventAdded(evid, zem))
            return evid

    def acknowledge(self, evids=None, ranges=None, start=None, limit=None,
                    sort=None, dir=None, filters=None, asof=None):
        zem = self._event_manager()
        r_evids = zem.getEventIDsFromRanges(self._dmd.Events, sort, dir, start,
                                        limit, filters, evids, ranges, asof)
        zem.manage_ackEvents(r_evids)
        for evid in r_evids:
            notify(EventAcknowledged(evid, zem))

    def unacknowledge(self, evids=None, ranges=None, start=None, limit=None,
                    sort=None, dir=None, filters=None, asof=None):
        zem = self._event_manager()
        r_evids = zem.getEventIDsFromRanges(self._dmd.Events, sort, dir, start,
                                        limit, filters, evids, ranges, asof)
        zem.manage_unackEvents(r_evids)
        for evid in r_evids:
            notify(EventUnacknowledged(evid, zem))

    def reopen(self, evids=None, ranges=None, start=None, limit=None,
                    sort=None, dir=None, filters=None, asof=None):
        zem = self._event_manager()
        r_evids = zem.getEventIDsFromRanges(self._dmd.Events, sort, dir, start,
                                        limit, filters, evids, ranges, asof)
        zem.manage_undeleteEvents(r_evids)
        for evid in r_evids:
            notify(EventReopened(evid, zem))

    def close(self, evids=None, ranges=None, start=None, limit=None,
                    sort=None, dir=None, filters=None, asof=None):
        zem = self._event_manager()
        r_evids = zem.getEventIDsFromRanges(self._dmd.Events, sort, dir, start,
                                        limit, filters, evids, ranges, asof)
        zem.manage_deleteEvents(r_evids)
        for evid in r_evids:
            notify(EventClosed(evid, zem))

