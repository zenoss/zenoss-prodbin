###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
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
import urllib
from Products.ZenUtils.Ext import DirectRouter
from AccessControl import getSecurityManager
from Products.ZenUtils.extdirect.router import DirectResponse
from Products.ZenUtils.Time import isoDateTimeFromMilli, isoToTimestamp
from Products.Zuul import getFacade
from Products.Zuul.decorators import require, serviceConnectionError
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier, IGUIDManager
from Products.ZenEvents.EventClass import EventClass
from Products.ZenEvents.events2.proxy import EventProxy
from Products.ZenMessaging.audit import audit
from zenoss.protocols.services.zep import EventStatus, EventSeverity
from zenoss.protocols.protobufs.zep_pb2 import EventSummary
from zenoss.protocols.protobufutil import ProtobufEnum
from zenoss.protocols.exceptions import NoConsumersException, PublishException
from json import loads
from Products.ZenUtils.deprecated import deprecated
from Products.Zuul.utils import resolve_context
from Products.Zuul.utils import ZuulMessageFactory as _t
from Products.ZenUI3.browser.eventconsole.grid import column_config
from Products.Zuul.interfaces import ICatalogTool

log = logging.getLogger('zen.%s' % __name__)

_status_name = ProtobufEnum(EventSummary,'status').getPrettyName
def _mergeAuditLogToNotes(evtsumm):
    if 'audit_log' in evtsumm:
        mergedNotes = evtsumm.get('notes',[])
        for auditNote in evtsumm['audit_log']:
            mergedNotes.append(
                {
                'created_time' : auditNote['timestamp'],
                'user_uuid' : auditNote.get('user_uuid', ''),
                'user_name' : auditNote.get('user_name', ''),
                'message' : 'state changed to %s' % _status_name(auditNote['new_status']),
                }
            )
        evtsumm['notes'] = mergedNotes
    return evtsumm

class EventsRouter(DirectRouter):
    """
    A JSON/ExtDirect interface to operations on events in ZEP
    """

    def __init__(self, context, request):
        super(EventsRouter, self).__init__(context, request)
        self.zep = getFacade('zep', context)
        self.catalog = ICatalogTool(context)
        self.manager = IGUIDManager(context.dmd)

    def _getPathFromUuid(self, uuid):
        if uuid:
            path = self.manager.getPath(uuid)
            if path:
                return urllib.unquote(path)

    def _getNameFromUuid(self, uuid):
        """
        Given a uuid this returns the objects name
        from the catalog, it does not wake the object up
        """
        if uuid:
            path = self._getPathFromUuid(uuid)
            if path:
                brain = self.catalog.getBrain(path)
                if brain:
                    return brain.name

    def _lookupEventClassMapping(self, mappingUuid):
        if not mappingUuid:
            return ""

        return {'uuid': mappingUuid, 'name': self._getNameFromUuid(mappingUuid)}

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
                details[d['name']] = d.get('value', ())
        return details


    def _singleDetail(self, value):
        """
        A convenience method for fetching a single detail from a property which
        correlates to a repeated field on the protobuf.
        """
        if isinstance(value, (tuple, list, set)) and value:
            return value[0]

    def _lookupDetailPath(self, prefix, values):
        if not values:
            return ()
        paths = []
        for value in values:
            paths.append({'uid': prefix + value, 'name': value})
        return paths

    def _get_device_url(self, eventDetails):
        url_and_path = [self._singleDetail(eventDetails.get(k)) for k in 'zenoss.device.url', 'zenoss.device.path']
        if len(url_and_path) != 2:
            return None
        url, path = url_and_path
        try:
            self.context.dmd.findChild(path)
        except:
            return None
        return url

    def _mapToOldEvent(self, event_summary):

        eventOccurrence = event_summary['occurrence'][0]
        eventActor = eventOccurrence['actor']
        eventClass = eventOccurrence['event_class']
        eventDetails = self._findDetails(eventOccurrence)

        event = {
            'id' : event_summary['uuid'],
            'evid' : event_summary['uuid'],
            'dedupid': eventOccurrence.get('fingerprint'),

            'eventState' : EventStatus.getPrettyName(event_summary['status']),
            'severity' : eventOccurrence['severity'],
            'component' : {
                'text': eventActor.get('element_sub_title'),
                'uid': self._getPathFromUuid(eventActor.get('element_sub_uuid')),
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
            'ownerid': event_summary.get('current_user_name'),
            'facility' : eventOccurrence.get('syslog_facility'),
            'priority' : eventOccurrence.get('syslog_priority'),
            'eventClassMapping' : self._lookupEventClassMapping(eventOccurrence.get('event_class_mapping_uuid')),
            'clearid' : event_summary.get('cleared_by_event_uuid'),
            'ntevid' : eventOccurrence.get('nt_event_code'),
            'ipAddress' : eventDetails.get('zenoss.device.ip_address', ''),
            'message' : eventOccurrence.get('message', ''),
            'Location' : self._lookupDetailPath('/zport/dmd/Locations', eventDetails.get(EventProxy.DEVICE_LOCATION_DETAIL_KEY)),
            'DeviceGroups' : self._lookupDetailPath('/zport/dmd/Groups', eventDetails.get(EventProxy.DEVICE_GROUPS_DETAIL_KEY)),
            'Systems' : self._lookupDetailPath('/zport/dmd/Systems', eventDetails.get(EventProxy.DEVICE_SYSTEMS_DETAIL_KEY)),
            'DeviceClass' : self._lookupDetailPath('/zport/dmd/Devices', eventDetails.get(EventProxy.DEVICE_CLASS_DETAIL_KEY)),
        }

        # if zenoss.device.url and zenoss.device.path are set and valid,
        #     then use those (use case is hub and collector daemon self-monitoring)
        #     otherwise determine the URL from actor.element_uuid
        device_url = self._get_device_url(eventDetails)
        if device_url is None:
            event['device'] = dict(text=eventActor.get('element_title'),
                                   uid=self._getPathFromUuid(eventActor.get('element_uuid')),
                                   url=self._uuidUrl(eventActor.get('element_uuid')),
                                   uuid=eventActor.get('element_uuid'))
        else:
            event['device'] = dict(text=eventActor.get('element_title'),
                                   url=device_url)

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
        try:
            values = []
            for t in value.split('/'):
                values.append(int(isoToTimestamp(t)) * 1000)
            return values
        except ValueError:
            log.warning("Invalid timestamp: %s", value)
            return ()

    def _filterInvalidUuids(self, events):
        """
        When querying archived events we need to make sure that
        we do not link to devices and components that are no longer valid
        """
        manager = self.manager
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

    @serviceConnectionError
    @require('ZenCommon')
    def queryArchive(self, page=None, limit=0, start=0, sort='lastTime', dir='desc', params=None, uid=None, detailFormat=False):
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


    @serviceConnectionError
    @require('ZenCommon')
    def query(self, limit=0, start=0, sort='lastTime', dir='desc', params=None,
              page=None, archive=False, uid=None, detailFormat=False):
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
        # special case for dmd/Devices in which case we want to show all events
        # by default events are not tagged with the root device classes because it would be on all events
        if uid == "/zport/dmd/Devices":
            uid = "/zport/dmd"
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


    @serviceConnectionError
    @require('ZenCommon')
    def queryGenerator(self, sort='lastTime', dir='desc', evids=None, excludeIds=None, params=None,
                       archive=False, uid=None, detailFormat=False):
        """
        Query for events.

        @type  sort: string
        @param sort: (optional) Key on which to sort the return results (default:
                     'lastTime')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'DESC')
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       (default: None)
        @type  archive: boolean
        @param archive: (optional) True to search the event archive instead
                        of active events (default: False)
        @type  uid: string
        @param uid: (optional) Context for the query (default: None)
        @rtype:   generator
        @return:  Generator returning events.
        """
        includeFilter, excludeFilter = self._buildRequestFilters(uid, params, evids, excludeIds)

        events = self.zep.getEventSummariesGenerator(filter=includeFilter, exclude=excludeFilter,
                                                      sort=self._buildSort(sort,dir), archive=archive)
        eventFormat = self._mapToOldEvent
        if detailFormat:
            eventFormat = self._mapToDetailEvent
        for event in events:
            yield eventFormat(event)

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
            if isinstance(params, basestring):
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
                status_change = params.get('stateChange') and self._timeRange(params.get('stateChange')),
                uuid = filterEventUuids,
                count_range = params.get('count'),
                element_title = params.get('device'),
                element_sub_title = params.get('component'),
                event_summary = params.get('summary'),
                current_user_name = params.get('ownerid'),
                agent = params.get('agent'),
                monitor = params.get('monitor'),
                fingerprint = params.get('dedupid'),

                # 'tags' comes from managed object guids.
                # see Zuul/security/security.py
                tags = params.get('tags'),

                details = details,
                event_key = params.get('eventKey'),

            )
            log.debug('Found params for building filter, ended up building  the following:')
            log.debug(event_filter)
        elif specificEventUuids:
            # if they passed in specific uuids but not other params
            event_filter = self.zep.createEventFilter(
                uuid = specificEventUuids
                )
        else:
            log.debug('Did not get parameters, using empty filter.')
            event_filter = {}

        if uid is None and isinstance(self.context, EventClass):
            uid = self.context

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

    def _mapToDetailEvent(self, event_summary):
        eventOccurrence = event_summary['occurrence'][0]
        eventClass = eventOccurrence['event_class']
        eventActor = eventOccurrence['actor']
        eventDetails = self._findDetails(eventOccurrence)
        eventClassMapping = self._lookupEventClassMapping(eventOccurrence.get('event_class_mapping_uuid'))
        eventClassMappingName = eventClassMappingUrl = None
        if eventClassMapping:
            eventClassMappingName = eventClassMapping['name']
            eventClassMappingUrl = self._uuidUrl(eventClassMapping['uuid'])

        # TODO: Update this mapping to more reflect _mapToOldEvent.
        eventData = {
            'evid':event_summary['uuid'],
            'device': eventActor.get('element_identifier'),
            'ipAddress': eventDetails.get('zenoss.device.ip_address', ''),
            'device_uuid':eventActor.get('element_uuid'),
            'component': eventActor.get('element_sub_identifier'),
            'component_title':self._getNameFromUuid(eventActor.get('element_sub_uuid')) or eventActor.get('element_sub_title'),
            'component_url':self._uuidUrl(eventActor.get('element_sub_uuid')),
            'component_uuid':eventActor.get('element_sub_uuid'),
            'firstTime':isoDateTimeFromMilli(event_summary['first_seen_time']),
            'lastTime':isoDateTimeFromMilli(event_summary['last_seen_time']),
            'stateChange':isoDateTimeFromMilli(event_summary['status_change_time']),
            'eventClass':eventClass,
            'eventClass_url':"/zport/dmd/Events%s" % eventClass,
            'eventKey':eventOccurrence.get('event_key'),
            'severity':eventOccurrence['severity'],
            'eventState':EventStatus.getPrettyName(event_summary['status']),
            'count':event_summary['count'],
            'summary':eventOccurrence.get('summary'),
            'message':eventOccurrence.get('message', ''),
            'dedupid':eventOccurrence['fingerprint'],
            'monitor':eventOccurrence.get('monitor'),
            'facility': eventOccurrence.get('syslog_facility'),
            'ntevid': eventOccurrence.get('nt_event_code'),
            'agent':eventOccurrence.get('agent'),
            'eventGroup': eventOccurrence.get('event_group'),
            'eventClassKey':eventOccurrence.get('event_class_key'),
            'Location' : self._lookupDetailPath('/zport/dmd/Locations', eventDetails.get(EventProxy.DEVICE_LOCATION_DETAIL_KEY)),
            'DeviceGroups' : self._lookupDetailPath('/zport/dmd/Groups', eventDetails.get(EventProxy.DEVICE_GROUPS_DETAIL_KEY)),
            'Systems' : self._lookupDetailPath('/zport/dmd/Systems', eventDetails.get(EventProxy.DEVICE_SYSTEMS_DETAIL_KEY)),
            'DeviceClass' : self._lookupDetailPath('/zport/dmd/Devices', eventDetails.get(EventProxy.DEVICE_CLASS_DETAIL_KEY)),
            'eventClassMapping': eventClassMappingName,
            'eventClassMapping_url': eventClassMappingUrl,
            'owner': event_summary.get('current_user_name'),
            'priority': eventOccurrence.get('syslog_priority'),
            'clearid': event_summary.get('cleared_by_event_uuid'),
            'log':[]}

        # if zenoss.device.url and zenoss.device.path are set and valid,
        #     then use those (use case is hub and collector daemon self-monitoring)
        #     otherwise determine the URL from actor.element_uuid
        device_url = self._get_device_url(eventDetails)
        if device_url is None:
            eventData['device_title'] = self._getNameFromUuid(eventActor.get('element_uuid')) or eventActor.get('element_title')
            eventData['device_url'] = self._uuidUrl(eventActor.get('element_uuid'))
        else:
            eventData['device_title'] = eventActor.get('element_title')
            eventData['device_url'] = device_url

        prodState = self._singleDetail(eventDetails.get('zenoss.device.production_state'))
        if prodState is not None:
            eventData['prodState'] = self.context.convertProdState(prodState)

        DevicePriority = self._singleDetail(eventDetails.get('zenoss.device.priority'))
        if DevicePriority is not None:
            eventData['DevicePriority'] = self.context.convertPriority(DevicePriority)

        event_summary = _mergeAuditLogToNotes(event_summary)
        if 'notes' in event_summary:
            event_summary['notes'].sort(key=lambda a:a['created_time'], reverse=True)
            for note in event_summary['notes']:
                eventData['log'].append((note['user_name'], isoDateTimeFromMilli(note['created_time']), note['message']))

        eventData['details'] = []
        if 'details' in eventOccurrence:
            for detail in sorted(eventOccurrence['details'], key=lambda detail: detail['name'].lower()):
                values = detail.get('value', ())
                if not isinstance(values, list):
                    values = list(values)
                for value in (v for v in values if v):
                    if not detail['name'].startswith('__meta__'):
                        eventData['details'].append(dict(key=detail['name'], value=value))
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

    @require('Manage Events')
    def postNote(self, uuid, note):
        self.zep.postNote(uuid, note)
        return DirectResponse.succeed()

    def _buildRequestFilters(self, uid, params, evids, excludeIds):
        """
        Given common request parameters, build the inclusive and exclusive
        filters for event update requests.
        """

        if uid is None and isinstance(self.context, EventClass):
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
    @deprecated
    def unacknowledge(self, *args, **kwargs):
        """
        Deprecated, Use reopen
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


    @require("Manage Events")
    def updateEventSummaries(self, update, event_filter=None, exclusion_filter=None, limit=None):
        status, response = self.zep.updateEventSummaries(update, event_filter, exclusion_filter, limit)
        return DirectResponse.succeed(data=response)


    @require('Manage Events')
    def add_event(self, summary, device, component, severity, evclasskey, evclass=None):
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
        try:
            self.zep.create(summary, severity, device, component, eventClassKey=evclasskey,
                            eventClass=evclass, immediate=True)
            return DirectResponse.succeed("Created event")
        except NoConsumersException:
            # This occurs if the event is queued but there are no consumers - i.e. zeneventd is not
            # currently running.
            msg = 'Queued event. Check zeneventd status on <a href="/zport/About/zenossInfo">Daemons</a>'
            return DirectResponse.succeed(msg, sticky=True)
        except PublishException, e:
            # This occurs if there is a failure publishing the event to the queue.
            log.exception("Failed creating event")
            return DirectResponse.exception(e, "Failed to create event")

    def _convertSeverityToNumber(self, sev):
        return EventSeverity.getNumber(sev)

    def _convertSeverityToName(self, sevId):
        return EventSeverity.getName(sevId)

    @property
    def configSchema(self):
        configSchema =[{
                'id': 'event_age_disable_severity',
                'name': _t("Don't Age This Severity and Above"),
                'xtype': 'eventageseverity',
                },{
                'id': 'event_age_severity_inclusive',
                'xtype': 'hidden',
                },{
                'id': 'event_age_interval_minutes',
                'name': _t('Event Aging Threshold (minutes)'),
                'xtype': 'numberfield',
                'minValue': 0,
                'allowNegative': False,
                },{
                'id': 'aging_interval_milliseconds',
                'name': _t('Event Aging Interval (milliseconds)'),
                'xtype': 'numberfield',
                'minValue': 0,
                'allowNegative': False
                },{
                'id': 'aging_limit',
                'name': _t('Event Aging Limit'),
                'xtype': 'numberfield',
                'minValue': 0,
                'allowNegative': False
                },{
                'id': 'event_archive_interval_minutes',
                'name': _t('Event Archive Threshold (minutes)'),
                'xtype': 'numberfield',
                'minValue': 1,
                'maxValue': 43200,
                'allowNegative': False,
                },{
                'id': 'archive_interval_milliseconds',
                'name': _t('Event Archive Interval (milliseconds)'),
                'xtype': 'numberfield',
                'minValue': 1,
                'maxValue': 43200,
                'allowNegative': False,
                },{
                'id': 'archive_limit',
                'name': _t('Event Archive Limit'),
                'xtype': 'numberfield',
                'minValue': 0,
                'allowNegative': False,
                },{
                'id': 'event_archive_purge_interval_days',
                'minValue': 1,
                'name': _t('Delete Archived Events Older Than (days)'),
                'xtype': 'numberfield',
                'allowNegative': False,
                },{
                'id': 'default_syslog_priority',
                'name': _t('Default Syslog Priority'),
                'xtype': 'numberfield',
                'allowNegative': False,
                'value': self.context.dmd.ZenEventManager.defaultPriority
                },{
                'id': 'default_availability_days',
                'name': _t('Default Availability Report (days)'),
                'xtype': 'numberfield',
                'allowNegative': False,
                'minValue': 1,
                'value': self.context.dmd.ZenEventManager.defaultAvailabilityDays
                },{
                'id': 'event_max_size_bytes',
                'name': _t('Max Event Size In Bytes'),
                'xtype': 'numberfield',
                'allowNegative': False,
                'minValue': 8192
                },{
                'id': 'index_summary_interval_milliseconds',
                'name': _t('Summary Index Interval (milliseconds)'),
                'xtype': 'numberfield',
                'allowNegative': False,
                'minValue': 0
                },{
                'id': 'index_archive_interval_milliseconds',
                'name': _t('Archive Index Interval (milliseconds)'),
                'xtype': 'numberfield',
                'allowNegative': False,
                'minValue': 0
                },{
                'id': 'index_limit',
                'name': _t('Index Limit'),
                'xtype': 'numberfield',
                'allowNegative': False,
                'minValue': 0
                },{
                'id': 'event_time_purge_interval_days',
                'name': _t('Event Time Purge Interval (days)'),
                'xtype': 'numberfield',
                'allowNegative': False,
                'minValue': 1
                }]
        return configSchema

    def _mergeSchemaAndZepConfig(self, data, configSchema):
        """
        Copy the values and defaults from ZEP to our schema
        """
        for conf in configSchema:
            if not data.get(conf['id']):
                continue
            prop = data[conf['id']]
            conf.update(prop)
        return configSchema

    @require('ZenCommon')
    def getConfig(self):
        # this data var is not a ZepConfig, it's a config structure that has been
        # constructed to include default values and be keyed by the protobuf
        # property name.
        data = self.zep.getConfig()
        config = self._mergeSchemaAndZepConfig(data, self.configSchema)
        return DirectResponse.succeed(data=config)

    @require('Manage DMD')
    def setConfigValues(self, values):
        """
        @type  values: Dictionary
        @param values: Key Value pairs of config values
        """
        # Remove empty strings from values
        empty_keys = [k for k,v in values.iteritems() if isinstance(v, basestring) and not len(v)]
        for empty_key in empty_keys:
            del values[empty_key]

        # we store default syslog priority and default availability days on the event manager
        defaultSyslogPriority = values.pop('default_syslog_priority', None)
        if defaultSyslogPriority is not None:
            self.context.dmd.ZenEventManager.defaultPriority = int(defaultSyslogPriority)

        defaultAvailabilityDays = values.pop('default_availability_days', None)
        if defaultAvailabilityDays is not None:
            self.context.dmd.ZenEventManager.defaultAvailabilityDays = int(defaultAvailabilityDays)

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

    @require('Manage Events')
    def clear_heartbeats(self):
        """
        Clear all heartbeat events

        @rtype:   DirectResponse
        @return:  B{Properties}:
           - success: (boolean) True if heartbeats deleted successfully
        """
        self.zep.deleteHeartbeats()
        audit('UI.Event.ClearHeartbeats', self.context)
        return DirectResponse.succeed()
