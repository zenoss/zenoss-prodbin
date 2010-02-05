###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from zope.event import notify
from zope.interface import implements
from Products.ZenUI3.utils.json import unjson
from Products.Zuul.utils import resolve_context
from Products.Zuul.facades import ZuulFacade
from Products.Zuul.interfaces import IEventEvent
from Products.Zuul.interfaces import IEventStateChanged
from Products.Zuul.interfaces import IEventAcknowledged
from Products.Zuul.interfaces import IEventUnacknowledged
from Products.Zuul.interfaces import IEventAdded
from Products.Zuul.interfaces import IEventReopened
from Products.Zuul.interfaces import IEventClosed
from Products.Zuul.interfaces import IEventFacade

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

class EventFacade(ZuulFacade):
    implements(IEventFacade)

    def _event_manager(self, history=False):
        if history:
            return self._dmd.ZenEventHistory
        else:
            return self._dmd.ZenEventManager

    def _get_device_url(self, devname):
        dev = self._dmd.Devices.findDevice(devname)
        if dev:
            return dev.absolute_url_path(), dev.titleOrId()
        else:
            return None, None

    def _get_component_url(self, dev, comp):
        comps = self._dmd.searchComponents(dev, comp)
        if comps:
            return comps[0].absolute_url_path(), comps[0].titleOrId()
        else:
            return None, None

    def _get_eventClass_url(self, evclass):
        return '/zport/dmd/Events' + evclass

    def _get_orderby_clause(self, sort, dir, history):
        secondarySort = self._event_manager(history).defaultOrderby
        if not secondarySort:
            secondarySort = 'lastTime DESC'
        orderBy = "%s %s, %s" % (sort, dir, secondarySort)
        return orderBy

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
                url, titleOrId = self._get_device_url(value)
                if url: data['device_url'] = url
                if titleOrId:
                    data['device_title'] = titleOrId
                else:
                    data['device_title'] = value
            elif field == 'component':
                dev = getattr(zevent, 'device', None)
                if dev:
                    url, titleOrId = self._get_component_url(dev, value)
                    if url: data['component_url'] = url
                    if titleOrId:
                        data['component_title'] = titleOrId
                    else:
                        data['component_title'] = value
            else:
                value = _shortvalue
            if field not in data:
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

    def fields(self, context=None, history=False):
        context = resolve_context(context, self._dmd.Events)
        zem = self._event_manager(history)
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
              filters=None, context=None, criteria=(), history=False):
        context = resolve_context(context, self._dmd.Events)
        if isinstance(filters, basestring): filters = unjson(filters)
        zem = self._event_manager(history)

        fields = self.fields(context, history)

        start = max(start, 0)
        limit = max(limit, 0)

        if not filters:
            filters = {}

        # Build parameterizedWhere
        # Currently supports only device and component specification
        if criteria:
            where = []
            vals = []
            for criterion in criteria:
                s = []
                # criterion is a dict
                for k, v in criterion.iteritems():
                    s.append('%s=%%s' % k)
                    vals.append(v)
                crit = ' and '.join(s)
                where.append('(%s)' % crit)
            crit = ' or '.join(where)
            parameterizedWhere = ('(%s)' % crit, vals)
        else:
            parameterizedWhere = None

        orderby = self._get_orderby_clause(sort, dir, history)
        args = dict(
            offset=start,
            rows=limit,
            resultFields=fields,
            getTotalCount=True,
            sort=sort,
            orderby=orderby,
            filters=filters,
            parameterizedWhere=parameterizedWhere
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

    def acknowledge(self, evids=None, excludeIds=None, selectState=None,
                    sort=None, dir=None, filters=None, asof=None,
                    context=None, history=False):
        context = resolve_context(context, self._dmd.Events)
        zem = self._event_manager(history)
        orderby = self._get_orderby_clause(sort, dir, history);
        r_evids = zem.getEventIds(context, selectState, orderby, filters, evids,
                                  excludeIds, asof)
        zem.manage_ackEvents(r_evids)
        for evid in r_evids:
            notify(EventAcknowledged(evid, zem))

    def unacknowledge(self, evids=None, excludeIds=None, selectState=None,
                    sort=None, dir=None, filters=None, asof=None,
                    context=None, history=False):
        context = resolve_context(context, self._dmd.Events)
        zem = self._event_manager(history)
        orderby = self._get_orderby_clause(sort, dir, history);
        r_evids = zem.getEventIds(context, selectState, orderby, filters, evids,
                                  excludeIds, asof)
        zem.manage_unackEvents(r_evids)
        for evid in r_evids:
            notify(EventUnacknowledged(evid, zem))

    def reopen(self, evids=None, excludeIds=None, selectState=None,
                    sort=None, dir=None, filters=None, asof=None,
                    context=None, history=False):
        context = resolve_context(context, self._dmd.Events)
        zem = self._event_manager(history)
        orderby = self._get_orderby_clause(sort, dir, history);
        r_evids = zem.getEventIds(context, selectState, orderby, filters, evids,
                                  excludeIds, asof)
        zem.manage_undeleteEvents(r_evids)
        for evid in r_evids:
            notify(EventReopened(evid, zem))

    def close(self, evids=None, excludeIds=None, selectState=None,
                    sort=None, dir=None, filters=None, asof=None,
                    context=None, history=False):
        context = resolve_context(context, self._dmd.Events)
        zem = self._event_manager(history)
        orderby = self._get_orderby_clause(sort, dir, history);
        r_evids = zem.getEventIds(context, selectState, orderby, filters, evids,
                                  excludeIds, asof)
        zem.manage_deleteEvents(r_evids)
        for evid in r_evids:
            notify(EventClosed(evid, zem))
