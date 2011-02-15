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
from uuid import uuid4
from zope.component import getUtility
from Products.ZenUtils.Ext import DirectRouter
from AccessControl import getSecurityManager
from Products.ZenUtils.extdirect.router import DirectResponse
from Products.ZenUtils.Time import isoDateTimeFromMilli
from Products.Zuul import getFacade
from Products.Zuul.decorators import require
from Products.ZenEvents.Event import Event as ZenEvent
from Products.ZenMessaging.queuemessaging.interfaces import IEventPublisher
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier, IGUIDManager
from Products.ZenEvents.EventClass import EventClass
from zenoss.protocols.services.zep import EventStatus, EventSeverity
from json import loads
from Products.Zuul.utils import resolve_context
from Products.Zuul.utils import ZuulMessageFactory as _t
from Products.ZenUI3.browser.eventconsole.grid import column_config

log = logging.getLogger('zen.%s' % __name__)

class EventsRouter(DirectRouter):
    """
    A JSON/ExtDirect interface to operations on events in ZEP
    """

    def __init__(self, context, request):
        super(EventsRouter, self).__init__(context, request)
        self.zep = getFacade('zep', context)
        self.api = getFacade('event', context)

    def _findDetails(self, event):
        """
        Event details are created as a dictionary like the following:
            detail = {
                'name': 'zenoss.foo.bar',
                'value': 'baz'
            }
        This method maps these detail items to a flat dictionary to facilitate
        looking up details by key easier.

        @rtype dict
        """
        details = {}
        if 'details' in event:
            for d in event['details']:
                details[d['name']] = d['value']
        return details


    def _singleDetail(self, value):
        """
        A convenience method for fetching a single detail from a property which
        correlates to a repeated field on the protobuf.
        """
        if isinstance(value, (tuple, list, set)) and value:
            return value[0]


    def _mapToOldEvent(self, event_summary):
        eventOccurrence = event_summary['occurrence'][0]
        eventActor = eventOccurrence['actor']

        eventClass = eventOccurrence['event_class']

        eventDetails = self._findDetails(eventOccurrence)

        # TODO: Finish mapping out these properties.
        notYetMapped = ''
        event = {
            'id' : event_summary['uuid'],
            'evid' : event_summary['uuid'],
            'dedupid': eventOccurrence.get('fingerprint'),

            'eventState' : EventStatus.getPrettyName(event_summary['status']),
            'severity' : eventOccurrence['severity'],
            'device' : {
                'text': eventActor.get('element_identifier'),
                'uid': None,
                'url' : self._uuidUrl(eventActor.get('element_uuid')),
                'uuid' : eventActor.get('element_uuid')
            },
            'component' : {
                'text': eventActor.get('element_sub_identifier'),
                'uid': None,
                'url' : self._uuidUrl(eventActor.get('element_sub_uuid')),
                'uuid' : eventActor.get('element_sub_uuid')
            },
            'eventClass' : {"text": eventClass, "uid": "/zport/dmd/Events%s" % eventClass},
            'summary' : eventOccurrence['summary'],
            'firstTime' : isoDateTimeFromMilli(event_summary['first_seen_time']),
            'lastTime' : isoDateTimeFromMilli(event_summary['last_seen_time'] ),
            'count' : event_summary['count'],

            'stateChange' : isoDateTimeFromMilli(event_summary['status_change_time']),
            'eventClassKey': eventOccurrence.get('event_class_key'),
            'eventGroup': eventOccurrence.get('event_group'),
            'eventKey' : eventOccurrence.get('event_key'),
            'agent': eventOccurrence.get('agent'),
            'monitor': eventOccurrence.get('monitor'),
            'ownerid': event_summary.get('acknowledged_by_user_name'),
            'facility' : eventOccurrence.get('syslog_facility'),
            'priority' : notYetMapped, # need to map from protobuf enum to Pretty Name.
            'eventClassMapping' : eventOccurrence.get('event_class_mapping_uuid'),
            'clearid' : event_summary.get('cleared_by_event_uuid'),
            'ntevid' : eventOccurrence.get('nt_event_code'),
            'ipAddress' : notYetMapped, # will be a detail
            'message' : eventOccurrence.get('message'),
            'Location' : notYetMapped, # comes from tags property
            'DeviceGroups' : notYetMapped, # comes from tags property
            'Systems' : notYetMapped, # comes from tags property
            'DeviceClass' : notYetMapped, # comes from tags property
        }


        prodState = self._singleDetail(eventDetails.get('zenoss.device.production_state'))
        if prodState is not None:
            event['prodState'] = self.context.convertProdState(prodState)

        DevicePriority = self._singleDetail(eventDetails.get('zenoss.device.priority'))
        if DevicePriority is not None:
            event['DevicePriority'] = self.context.convertPriority(DevicePriority)


        # make custom details actually show up. This does not include the manually
        # mapped zenoss details.
        for d in self.zep.getUnmappedDetails():
            event[d['key']] = eventDetails.get(d['key'])

        return event


    def _timeRange(self, value):
        values = []
        for t in value.split('/'):
            values.append(DateTime.DateTime(t, datefmt='us').millis())
        return values

    def _filterInvalidUuids(self, events):
        """
        When querying archived events we need to make sure that
        we do not link to devices and components that are no longer valid
        """
        manager = IGUIDManager(self.context.dmd)
        for event_summary in events:
            occurrence = event_summary['occurrence'][0]
            actor = occurrence['actor']
            # element
            if actor.get('element_uuid') and \
                   actor.get('element_uuid') not in manager.table:
                del actor['element_uuid']

            # sub element
            if actor.get('element_sub_uuid') and \
                   actor.get('element_sub_uuid') not in manager.table:
                del actor['element_sub_uuid']
            yield event_summary

    @require('ZenCommon')
    def queryArchive(self, limit=0, start=0, sort='lastTime', dir='desc', params=None, uid=None, detailFormat=False):
        filter = self._buildFilter(uid, params)

        events = self.zep.getEventSummariesFromArchive(limit=limit, offset=start, sort=self._buildSort(sort,dir),
                                                       filter=filter)

        eventFormat = self._mapToOldEvent
        if detailFormat:
            eventFormat = self._mapToDetailEvent
        # filter out the component and device UUIDs that no longer exist in our system
        evdata = self._filterInvalidUuids(events['events'])
        return DirectResponse.succeed(
            events = [eventFormat(e) for e in evdata],
            totalCount = events['total'],
            asof = time.time()
        )

    @require('ZenCommon')
    def query(self, limit=0, start=0, sort='lastTime', dir='desc', params=None,
              archive=False, uid=None, detailFormat=False):
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
        @rtype:   dictionary
        @return:  B{Properties}:
           - events: ([dictionary]) List of objects representing events
           - totalCount: (integer) Total count of events returned
           - asof: (float) Current time
        """
        if archive:
            return self.queryArchive(limit=limit, start=start, sort=sort,
                                     dir=dir, params=params, uid=uid,
                                     detailFormat=detailFormat)

        filter = self._buildFilter(uid, params)

        events = self.zep.getEventSummaries(limit=limit, offset=start, sort=self._buildSort(sort,dir), filter=filter)

        eventFormat = self._mapToOldEvent
        if detailFormat:
            eventFormat = self._mapToDetailEvent

        return DirectResponse.succeed(
            events = [eventFormat(e) for e in events['events']],
            totalCount = events['total'],
            asof = time.time()
        )

    def _buildSort(self, sort='lastTime', dir='desc'):
        sort_list = [(sort,dir)]
        # Add secondary sort of last time descending
        if sort not in ('lastTime','evid'):
            sort_list.append(('lastTime','desc'))
        return sort_list

    def _buildFilter(self, uid, params, specificEventUuids=None):
        """
        Construct a dictionary that can be converted into an EventFilter protobuf.

        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       (default: None)
        @type  uid: string
        @param uid: (optional) Context for the query (default: None)
        """


        if params:
            log.debug('logging params for building filter: %s', params)
            params = loads(params)


            # params comes from the grid's filtering column -
            # some of these properties are normal properties on an event
            # while others are considered event details. Separate the
            # two here.
            params, details = self.zep.parseParameterDetails(params)

            filterEventUuids = []

            # No specific event uuids passed in-
            # check for event ids from the grid parameters
            if specificEventUuids is None:
                log.debug('No specific event uuids were passed in.')

                # The evid's from params only ever mean anything for filtering - if
                # specific uuids are passed in, this filter will ignore the grid
                # parameters and just act on or filter using these specific event uuids.
                evid = params.get('evid')
                if evid:
                    if not isinstance(evid,(list, tuple)):
                        evid = [evid]
                    filterEventUuids.extend(evid)

            # Specific event uuids were passed in, use those for this filter.
            else:
                log.debug('Specific event uuids passed in: %s', specificEventUuids)
                if not isinstance(specificEventUuids,(list, tuple)):
                    filterEventUuids = [specificEventUuids]
                else:
                    filterEventUuids = specificEventUuids

            log.debug('FilterEventUuids is: %s', filterEventUuids)
            
            event_filter = self.zep.createEventFilter(
                severity = params.get('severity'),
                status = [i for i in params.get('eventState', [])],
                event_class = filter(None, [params.get('eventClass')]),
                first_seen = params.get('firstTime') and self._timeRange(params.get('firstTime')),
                last_seen = params.get('lastTime') and self._timeRange(params.get('lastTime')),
                uuid = filterEventUuids,
                count_range = params.get('count'),
                element_identifier = params.get('device'),
                element_sub_identifier = params.get('component'),
                event_summary = params.get('summary'),
                acknowledged_by_user_name = params.get('ownerid'),
                agent = params.get('agent'),
                monitor = params.get('monitor'),

                # 'tags' comes from managed object guids.
                # see Zuul/security/security.py
                tags = params.get('tags'),

                details = details

            )
            log.debug('Found params for building filter, ended up building  the following:')
            log.debug(event_filter)
        else:
            log.debug('Did not get parameters, using empty filter.')
            event_filter = {}

        if uid is None:
            uid = self.context.dmd.Events

        context = resolve_context(uid)

        if context and context.id not in ('Events', 'dmd'):
            try:
                # make a specific instance of tag_filter just for the context tag.
                context_tag_filter = {
                    'tag_uuids': [IGlobalIdentifier(context).getGUID()]
                }
                # if it exists, filter['tag_filter'] will be a list. just append the special
                # context tag filter to whatever that list is.
                tag_filter = event_filter.setdefault('tag_filter', [])
                tag_filter.append(context_tag_filter)
            except TypeError:
                if isinstance(context, EventClass):
                    event_filter['event_class'] = [context.getDmdKey()]
                else:
                    raise Exception('Unknown context %s' % context)

        log.debug('Final filter will be:')
        log.debug(event_filter)

        return event_filter

    def _uuidUrl(self, uuid):
        if uuid:
            return '/zport/dmd/goto?guid=%s' % uuid

    @require('ZenCommon')

    def _mapToDetailEvent(self, event_summary):
        eventOccurrence = event_summary['occurrence'][0]
        eventClass = eventOccurrence['event_class']
        

        # TODO: Update this mapping to more reflect _mapToOldEvent.
        eventData = {
            'evid':event_summary['uuid'],
            'device':eventOccurrence['actor'].get('element_identifier', None),
            'device_title':eventOccurrence['actor'].get('element_identifier', None),
            'device_url':self._uuidUrl(eventOccurrence['actor'].get('element_uuid', None)),
            'device_uuid':eventOccurrence['actor'].get('element_uuid', None),
            'component':eventOccurrence['actor'].get('element_sub_identifier', None),
            'component_title':eventOccurrence['actor'].get('element_sub_identifier', None),
            'component_url':self._uuidUrl(eventOccurrence['actor'].get('element_sub_uuid', None)),
            'component_uuid':eventOccurrence['actor'].get('element_sub_uuid', None),
            'firstTime':isoDateTimeFromMilli(event_summary['first_seen_time']),
            'lastTime':isoDateTimeFromMilli(event_summary['last_seen_time']),
            'eventClass':eventClass,
            'eventClass_url':"/zport/dmd/Events%s" % eventClass,
            'severity':eventOccurrence['severity'],
            'eventState':EventStatus.getPrettyName(event_summary['status']),
            'count':event_summary['count'],
            'summary':eventOccurrence.get('summary'),
            'message':eventOccurrence.get('message'),
            'properties':[
                dict(key=k, value=v) for (k, v) in {'evid':event_summary['uuid'],
                                                    'device':eventOccurrence['actor'].get('element_identifier', None),
                                                    'component':eventOccurrence['actor'].get('element_sub_identifier', None),
                                                    'firstTime':isoDateTimeFromMilli(event_summary['first_seen_time']),
                                                    'lastTime':isoDateTimeFromMilli(event_summary['last_seen_time']),
                                                    'stateChange':isoDateTimeFromMilli(event_summary['status_change_time']),
                                                    'dedupid':eventOccurrence['fingerprint'],
                                                    'eventClass':eventClass,
                                                    'eventClassKey':eventOccurrence['event_class'],
                                                    'eventClassMapping_uuid':self._uuidUrl(eventOccurrence.get('event_class_mapping_uuid')),
                                                    'eventKey':eventOccurrence.get('event_key', None),
                                                    'summary':eventOccurrence.get('summary'),
                                                    'severity':eventOccurrence.get('severity'),
                                                    'eventState':EventStatus.getPrettyName(event_summary['status']),
                                                    'count':event_summary['count'],
                                                    'monitor':eventOccurrence.get('monitor'),
                                                    'agent':eventOccurrence.get('agent'),
                                                    'message':eventOccurrence.get('message')}.iteritems() if v],
            'log':[]}
        if 'notes' in event_summary:
            for note in event_summary['notes']:
                eventData['log'].append((note['user_name'], isoDateTimeFromMilli(note['created_time']), note['message']))

        if 'details' in eventOccurrence:
            for detail in eventOccurrence['details']:
                values = detail['value']
                if not isinstance(values, list):
                    values = list(values)
                for value in (v for v in values if v):
                    if not detail['name'].startswith('__meta__'):
                        eventData['properties'].append(dict(key=detail['name'], value=value))

        return eventData

    def detail(self, evid):
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
            eventData = self._mapToDetailEvent(event_summary)

            return DirectResponse.succeed(event=[eventData])
        else:
            raise Exception('Could not find event %s' % evid)

    @require('Manage Events')
    def write_log(self, evid=None, message=None):
        """
        Write a message to an event's log.

        @type  evid: string
        @param evid: Event ID to log to
        @type  message: string
        @param message: Message to log
        @rtype:   DirectResponse
        @return:  Success message
        """

        userName = getSecurityManager().getUser().getId()

        self.zep.addNote(uuid=evid, message=message, userName=userName)

        return DirectResponse.succeed()

    def _buildRequestFilters(self, uid, params, evids, excludeIds):
        """
        Given common request parameters, build the inclusive and exclusive
        filters for event update requests.
        """

        if uid is None:
            uid = self.context

        log.debug('Context while building request filters is: %s', uid)
        
        # if the request contains specific event summaries to act on, they will
        # be passed in as evids. Excluded event summaries are passed in under
        # the keyword argument 'excludeIds'. If these exist, pass them in as
        # parameters to be used to construct the EventFilter.
        includeUuids = None
        if isinstance(evids, (list, tuple)):
            log.debug('Found specific event ids, adding to params.')
            includeUuids = evids
        
        includeFilter = self._buildFilter(uid, params, specificEventUuids=includeUuids)
        
        # the only thing excluded in an event filter is a list of event uuids
        # which are passed as EventTagFilter using the OR operator.
        excludeFilter = None
        if excludeIds:
            excludeFilter = self._buildFilter(uid, params, specificEventUuids=excludeIds.keys())
        
        log.debug('The exclude filter:' + str(excludeFilter))
        log.debug('Finished building request filters.')

        return includeFilter, excludeFilter

    @require('Manage Events')
    def nextEventSummaryUpdate(self, next_request):
        """
        When performing updates from the event console, updates are performed in batches
        to allow the user to see the progress of event changes and cancel out of updates
        while they are in progress. This works by specifying a limit to one of the close,
        acknowledge, or reopen calls in this router. The response will contain an
        EventSummaryUpdateResponse, and if there are additional updates to be performed,
        it will contain a next_request field with all of the parameters used to update
        the next range of events.

        @type  next_request: dictionary
        @param next_request: The next_request field from the previous updates.
        """
        log.debug('Starting next batch of updates')
        status, summaryUpdateResponse = self.zep.nextEventSummaryUpdate(next_request)

        log.debug('Completed updates: %s', summaryUpdateResponse)
        return DirectResponse.succeed(data=summaryUpdateResponse)

    @require('Manage Events')
    def close(self, evids=None, excludeIds=None, params=None, uid=None, asof=None, limit=None):
        """
        Close event(s).

        @type  evids: [string]
        @param evids: (optional) List of event IDs to close (default: None)
        @type  excludeIds: [string]
        @param excludeIds: (optional) List of event IDs to exclude from
                           close (default: None)
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       (default: None)
        @type  uid: string
        @param uid: (optional) Context for the query (default: None)
        @type  asof: float
        @param asof: (optional) Only close if there has been no state
                     change since this time (default: None)
        @type  limit: The maximum number of events to update in this batch.
        @param limit: (optional) Maximum number of events to update (default: None).
        @rtype:   DirectResponse
        @return:  Success message
        """

        log.debug('Issuing a close request.')

        includeFilter, excludeFilter = self._buildRequestFilters(uid, params, evids, excludeIds)
        
        status, summaryUpdateResponse = self.zep.closeEventSummaries(
            eventFilter=includeFilter,
            exclusionFilter=excludeFilter,
            limit=limit,
        )

        log.debug('Done issuing close request.')
        log.debug(summaryUpdateResponse)

        return DirectResponse.succeed(data=summaryUpdateResponse)

    @require('Manage Events')
    def acknowledge(self, evids=None, excludeIds=None, params=None, uid=None, asof=None, limit=None):
        """
        Acknowledge event(s).

        @type  evids: [string]
        @param evids: (optional) List of event IDs to acknowledge (default: None)
        @type  excludeIds: [string]
        @param excludeIds: (optional) List of event IDs to exclude from
                           acknowledgment (default: None)
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       (default: None)
        @type  uid: string
        @param uid: (optional) Context for the query (default: None)
        @type  asof: float
        @param asof: (optional) Only acknowledge if there has been no state
                     change since this time (default: None)
        @type  limit: The maximum number of events to update in this batch.
        @param limit: (optional) Maximum number of events to update (default: None).
        @rtype:   DirectResponse
        @return:  Success message
        """
        log.debug('Issuing an acknowledge request.')
        
        includeFilter, excludeFilter = self._buildRequestFilters(uid, params, evids, excludeIds)
        
        status, summaryUpdateResponse = self.zep.acknowledgeEventSummaries(
            eventFilter=includeFilter,
            exclusionFilter=excludeFilter,
            limit=limit,
        )

        log.debug('Done issuing acknowledge request.')
        log.debug(summaryUpdateResponse)

        return DirectResponse.succeed(data=summaryUpdateResponse)

    @require('Manage Events')
    def unacknowledge(self, *args, **kwargs):
        """
        @Deprecated Use reopen
        """
        return self.reopen(*args, **kwargs)

    @require('Manage Events')
    def reopen(self, evids=None, excludeIds=None, params=None, uid=None, asof=None, limit=None):
        """
        Reopen event(s).

        @type  evids: [string]
        @param evids: (optional) List of event IDs to reopen (default: None)
        @type  excludeIds: [string]
        @param excludeIds: (optional) List of event IDs to exclude from
                           reopen (default: None)
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       (default: None)
        @type  uid: string
        @param uid: (optional) Context for the query (default: None)
        @type  asof: float
        @param asof: (optional) Only reopen if there has been no state
                     change since this time (default: None)
        @type  limit: The maximum number of events to update in this batch.
        @param limit: (optional) Maximum number of events to update (Default: None).
        @rtype:   DirectResponse
        @return:  Success message
        """

        log.debug('Issuing a reopen request.')

        includeFilter, excludeFilter = self._buildRequestFilters(uid, params, evids, excludeIds)

        status, summaryUpdateResponse = self.zep.reopenEventSummaries(
            eventFilter=includeFilter,
            exclusionFilter=excludeFilter,
            limit=limit,
        )

        log.debug('Done issuing reopen request.')
        log.debug(summaryUpdateResponse)

        return DirectResponse.succeed(data=summaryUpdateResponse)

    @require('Manage Events')
    def add_event(self, summary, device, component, severity, evclasskey, evclass):
        """
        Create a new event.

        @type  summary: string
        @param summary: New event's summary
        @type  device: string
        @param device: Device uid to use for new event
        @type  component: string
        @param component: Component uid to use for new event
        @type  severity: string
        @param severity: Severity of new event. Can be one of the following:
                         Critical, Error, Warning, Info, Debug, or Clear
        @type  evclasskey: string
        @param evclasskey: The Event Class Key to assign to this event
        @type  evclass: string
        @param evclass: Event class for the new event
        @rtype:   DirectResponse
        """

        event = ZenEvent(
            evid=str(uuid4()),
            summary=summary,
            device=device,
            component=component,
            severity=severity,
            eventClassKey=evclasskey,
            eventClass=evclass,
        )
        publisher = getUtility(IEventPublisher)
        publisher.publish(event, mandatory=True)

        return DirectResponse.succeed(evid=event.evid)

    def _convertSeverityToNumber(self, sev):
        return EventSeverity.getNumber(sev)

    def _convertSeverityToName(self, sevId):
        return EventSeverity.getName(sevId)

    @property
    def configSchema(self):
        configSchema =[{
                'id': 'event_age_disable_severity',
                'name': _t("Don't Age This Severity and Above"),
                'xtype': 'severity',
                'fromZep': self._convertSeverityToNumber,
                'toZep': self._convertSeverityToName,
                },{
                'id': 'event_age_interval_minutes',
                'name': _t('Event Aging Threshold (minutes)'),
                'xtype': 'numberfield',
                'minValue': 60,
                'allowNegative': False,
                },{
                'id': 'event_archive_interval_days',
                'name': _t('Event Archive Interval (days)'),
                'xtype': 'numberfield',
                'minValue': 1,
                'maxValue': 30,
                'allowNegative': False,
                },{
                'id': 'event_archive_purge_interval_days',
                'maxValue': 90,
                'name': _t('Delete Historical Events Older Than (days)'),
                'xtype': 'numberfield',
                'allowNegative': False,
                },{
                'id': 'event_occurrence_purge_interval_days',
                'maxValue': 30,
                'name': _t('Event Occurrence Purge Interval (days)'),
                'xtype': 'numberfield',
                'allowNegative': False,
                },{
                'id': 'default_syslog_priority',
                'name': _t('Default Syslog Priority'),
                'xtype': 'numberfield',
                'allowNegative': False,
                'value': self.context.dmd.ZenEventManager.defaultPriority
                }]
        return configSchema

    def _mergeSchemaAndZepConfig(self, data, config):
        """
        Copy the values and defaults from ZEP to our schema
        """
        for conf in config:
            if not data.get(conf['id']):
                continue
            prop = data[conf['id']]
            for key in prop.keys():
                conf[key] = prop[key]
            # our drop down expects severity to be the number constant
            if conf.get('fromZep'):
                conf['defaultValue'] = conf['fromZep']((prop['defaultValue']))
                if prop['value']:
                    conf['value'] = conf['fromZep']((prop['value']))
                del conf['fromZep']
            if conf.get('toZep'):
                del conf['toZep']
        return config

    @require('ZenCommon')
    def getConfig(self):
        data = self.zep.getConfig()
        config = self._mergeSchemaAndZepConfig(data, self.configSchema)
        return DirectResponse.succeed(data=config)

    @require('Manage DMD')
    def setConfigValues(self, values):
        """
        @type  values: Dictionary
        @param values: Key Value pairs of config values
        """
        for config in self.configSchema:
            id = config['id']
            if config.get('toZep'):
                values[id] = config['toZep'](values[id])

        # we store default syslog priority on the event manager
        if values.get('default_syslog_priority'):
            pri = values.get('default_syslog_priority')
            self.context.dmd.ZenEventManager.defaultPriority = pri
            del values['default_syslog_priority']
        self.zep.setConfigValues(values)
        return DirectResponse.succeed()

    def column_config(self, uid=None, archive=False):
        """
        Get the current event console field column configuration.

        @type  uid: string
        @param uid: (optional) UID context to use (default: None)
        @type  archive: boolean
        @param archive: (optional) True to use the event archive instead
                        of active events (default: False)
        @rtype:   [dictionary]
        @return:  A list of objects representing field columns
        """
        return column_config(self.request, archive)

    @require('Manage Events')
    def classify(self, evrows, evclass):
        """
        Associate event(s) with an event class.

        @type  evrows: [dictionary]
        @param evrows: List of event rows to classify
        @type  evclass: string
        @param evclass: Event class to associate events to
        @rtype:   DirectResponse
        @return:  B{Properties}:
           - msg: (string) Success/failure message
           - success: (boolean) True if class update successful
        """
        msg, url = self.zep.createEventMapping(evrows, evclass)
        if url:
            msg += "<br/><a href='%s'>Go to the new mapping.</a>" % url
        return DirectResponse(msg, success=bool(url))
