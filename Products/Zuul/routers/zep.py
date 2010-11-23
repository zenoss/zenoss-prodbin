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
"""
Operations for Events.

Available at:  /zport/dmd/evconsole_router
"""

import time
import logging
import DateTime # Zope DateTime, not python datetime
from Products.ZenUtils.Ext import DirectRouter
from Products.ZenUtils.extdirect.router import DirectResponse
from Products.Zuul import getFacade
from Products.Zuul.decorators import require
from Products.Zuul.routers.events import EventsRouter
from datetime import datetime
from zenoss.protocols.protobufs.zep_pb2 import EventSummary, Event
from zenoss.protocols.services.zep import EventSeverity, EventStatus
from json import loads
from Products.Zuul.utils import resolve_context
log = logging.getLogger(__name__)


# TODO Temporarily extend EventsRouter till all methods are implemented
class ZepRouter(EventsRouter):
    """
    A JSON/ExtDirect interface to operations on events in ZEP
    """

    _sortMap = {
        'eventState' : 'status',
        'severity' : 'event_severity',
        'firstTime' : 'first_seen_time',
        'lastTime' : 'last_seen_time',
        'eventClass' : 'event_event_class',
        'device' : 'event_actor_element_identifier',
        'component' : 'event_actor_element_sub_identifier',
        'count' : 'count',
    }

    def __init__(self, context, request):
        super(ZepRouter, self).__init__(context, request)
        self.zep = getFacade('zep', context)
        self.api = getFacade('event', context)

    def _mapToOldEvent(self, event_summary):
        eventOccurrence = event_summary['occurrence'][0]

        eventClass = eventOccurrence['event_class']

        # FIXME Lookup the item by UUID to create a link, or better yet just use the UUID in the front end
        #element = eventOccurrence['actor'].get('element_identifier', None)
        #if element:
        #    IGuidManager(self._dmd).getObject(uuid)

        event = {
            'id' : event_summary['uuid'],
            'evid' : event_summary['uuid'],
            'device' : {
                'text': eventOccurrence['actor'].get('element_identifier', None),
                'uid': None,
                'uuid' : eventOccurrence['actor'].get('element_uuid', None)
            },
            'component' : {
                'text': eventOccurrence['actor'].get('element_sub_identifier', None),
                'uid': None,
                'uuid' : eventOccurrence['actor'].get('element_sub_uuid', None)
            },
            'firstTime' : str(datetime.utcfromtimestamp(event_summary['first_seen_time'] / 1000)),
            'lastTime' : str(datetime.utcfromtimestamp(event_summary['last_seen_time'] / 1000)),
            'eventClass' : {"text": eventClass, "uid": "/zport/dmd/Events%s" % eventClass},
            'eventKey' : eventOccurrence.get('event_key', None),
            'summary' : eventOccurrence['summary'],
            'severity' : eventOccurrence['severity'],
            'eventState' : EventStatus.getPrettyName(event_summary['status']),
            'count' : event_summary['count'],
        }

        return event

    def _timeRange(self, value):
        values = []
        for t in value.split('/'):
            values.append(DateTime.DateTime(t, datefmt='us').millis())
        return values

    @require('ZenCommon')
    def query(self, limit=0, start=0, sort='lastTime', dir='desc', params=None,
              history=False, uid=None, criteria=()):
        """
        Query for events.

        @type  limit: integer
        @param limit: (optional) Max index of events to retrieve (default: 0)
        @type  start: integer
        @param start: (optional) Min index of events to retrieve (default: 0)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return results (default:
                     'lastTime')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'DESC')
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       (default: None)
        @type  history: boolean
        @param history: (optional) True to search the event history table instead
                        of active events (default: False)
        @type  uid: string
        @param uid: (optional) Context for the query (default: None)
        @type  criteria: [dictionary]
        @param criteria: (optional) A list of key-value pairs to to build query's
                         where clause (default: None)
        @rtype:   dictionary
        @return:  B{Properties}:
           - events: ([dictionary]) List of objects representing events
           - totalCount: (integer) Total count of events returned
           - asof: (float) Current time
        """
        if params:
            params = loads(params)
            filter = self.zep.createFilter(
                summary = params.get('summary'),
                event_class = params.get('eventClass'),
                # FIXME Front end has the status off by one, has many places in JS this would need to be fixed
                status = [i + 1 for i in params.get('eventState', [])],
                severity = params.get('severity'),
                tags = params.get('tags'),
                count = params.get('count'),
                element_identifier = params.get('device'),
                element_sub_identifier = params.get('component'),
                first_seen = params.get('firstTime') and self._timeRange(params.get('firstTime')),
                last_seen = params.get('lastTime') and self._timeRange(params.get('lastTime')),
            )
        else:
            filter = {}

        if uid is None:
            uid = self.context

        context = resolve_context(uid)

        if context and context.id != 'Events':
            tags = filter.get('tag_uuids', [])
            tags.append(context.uuid)
            filter['tag_uuids'] = tags

        if sort in self._sortMap:
            sort = self._sortMap[sort]
        else:
            raise Exception('"%s" is not a valid sort option' % sort)

        events = self.zep.getEventSummaries(limit=limit, offset=start, sort=sort+'-'+dir.lower(), filter=filter)

        return DirectResponse.succeed(
            events = [self._mapToOldEvent(e) for e in events['events']],
            totalCount = events['total'],
            asof = time.time()
        )

    @require('ZenCommon')
    def detail(self, evid, history=False):
        """
        Get event details.

        @type  evid: string
        @param evid: Event ID to get details
        @type  history: boolean
        @param history: Deprecated
        @rtype:   DirectResponse
        @return:  B{Properties}:
           - event: ([dictionary]) List containing a dictionary representing
                    event details
        """
        event_summary = self.zep.getEventSummary(evid)
        if event_summary:
            eventOccurrence = event_summary['occurrence'][0]

            eventClass = eventOccurrence['event_class']
            print eventOccurrence
            eventData = {
                'evid' : event_summary['uuid'],
                'device' : eventOccurrence['actor'].get('element_identifier', None),
                'device_title' : eventOccurrence['actor'].get('element_identifier', None),
                'device_url' : None,
                'device_uuid' : eventOccurrence['actor'].get('element_uuid', None),
                'component' : eventOccurrence['actor'].get('element_sub_identifier', None),
                'component_title' : eventOccurrence['actor'].get('element_sub_identifier', None),
                'component_url' : None,
                'component_uuid' : eventOccurrence['actor'].get('element_sub_uuid', None),
                'firstTime' : str(datetime.utcfromtimestamp(event_summary['first_seen_time'] / 1000)),
                'lastTime' : str(datetime.utcfromtimestamp(event_summary['last_seen_time'] / 1000)),
                'eventClass' : eventClass,
                'eventClass_url' : "/zport/dmd/Events%s" % eventClass,
                'severity' : eventOccurrence['severity'],
                'eventState' : EventStatus.getPrettyName(event_summary['status']),
                'count' : event_summary['count'],
                'summary' : eventOccurrence.get('summary'),
                'message' : eventOccurrence.get('message'),
                'properties' : {
                    'evid' : event_summary['uuid'],
                    'device' : eventOccurrence['actor'].get('element_identifier', None),
                    'component' : eventOccurrence['actor'].get('element_sub_identifier', None),
                    'firstTime' : str(datetime.utcfromtimestamp(event_summary['first_seen_time'] / 1000)),
                    'lastTime' : str(datetime.utcfromtimestamp(event_summary['last_seen_time'] / 1000)),
                    'stateChange' : str(datetime.utcfromtimestamp(event_summary['status_change_time'] / 1000)),
                    'dedupid' : eventOccurrence['fingerprint'],
                    'eventClass' : eventClass,
                    'eventClassKey' :  eventOccurrence['event_class'],
                    'eventClassMapping_uuid' :  eventOccurrence.get('event_class_mapping_uuid'),
                    'eventKey' : eventOccurrence.get('event_key', None),
                    'summary' : eventOccurrence.get('summary'),
                    'severity' : eventOccurrence.get('severity'),
                    'eventState' : EventStatus.getPrettyName(event_summary['status']),
                    'count' : event_summary['count'],
                    'monitor' : eventOccurrence.get('monitor'),
                    'agent' : eventOccurrence.get('agent'),
                    'message' : eventOccurrence.get('message'),
                },
                'log' : []
            }

            if 'details' in eventOccurrence:
                for detail in eventOccurrence['details']:
                    eventData['properties'][detail['name']] = detail['value']

            return DirectResponse.succeed(event=[eventData])
        else:
            raise Exception('Could not find event %s' % evid)