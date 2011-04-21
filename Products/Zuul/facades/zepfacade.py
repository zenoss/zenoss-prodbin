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

import logging
import re
from AccessControl import getSecurityManager
from zope.interface import implements
from Products.ZenModel.Device import Device
from Products.Zuul.facades import ZuulFacade
from Products.Zuul.interfaces import IZepFacade
from Products.ZenEvents.ZenEventClasses import Unknown

import pkg_resources
from zenoss.protocols.services.zep import ZepServiceClient, EventSeverity, ZepConfigClient, ZepHeartbeatClient
from zenoss.protocols.jsonformat import to_dict, from_dict
from zenoss.protocols.protobufs.zep_pb2 import EventSort, EventFilter, EventSummaryUpdateRequest, ZepConfig
from zenoss.protocols.protobufutil import listify
from Products.ZenUtils import safeTuple
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from zenoss.protocols.protobufs.zep_pb2 import SEVERITY_CRITICAL, SEVERITY_ERROR, SEVERITY_WARNING, SEVERITY_INFO, \
     SEVERITY_DEBUG, SEVERITY_CLEAR, STATUS_NEW, STATUS_ACKNOWLEDGED, STATUS_SUPPRESSED, OR, AND
from Products.ZenUtils.guid.interfaces import IGUIDManager
from Products.ZenEvents.ZenEventClasses import Status_Ping
from functools import partial

log = logging.getLogger(__name__)

class ZepFacade(ZuulFacade):
    implements(IZepFacade)

    AND = AND
    OR = OR

    DEFAULT_SORT_MAP = {
        'eventstate':  { 'field': EventSort.STATUS },
        'severity':    { 'field': EventSort.SEVERITY },
        'firsttime':   { 'field': EventSort.FIRST_SEEN },
        'lasttime':    { 'field': EventSort.LAST_SEEN },
        'eventclass':  { 'field': EventSort.EVENT_CLASS },
        'device':      { 'field': EventSort.ELEMENT_IDENTIFIER },
        'component':   { 'field': EventSort.ELEMENT_SUB_IDENTIFIER },
        'count':       { 'field': EventSort.COUNT },
        'summary':     { 'field': EventSort.EVENT_SUMMARY },
        'ownerid':     { 'field': EventSort.CURRENT_USER_NAME },
        'agent':       { 'field': EventSort.AGENT },
        'monitor':     { 'field': EventSort.MONITOR },
        'evid':        { 'field': EventSort.UUID },
        'statechange': { 'field': EventSort.STATUS_CHANGE },
    }

    SORT_DIRECTIONAL_MAP = {
        'asc' : EventSort.ASCENDING,
        'desc' : EventSort.DESCENDING,
    }

    ZENOSS_DETAIL_OLD_TO_NEW_MAPPING = {
        'prodState': 'zenoss.device.production_state',
        'DevicePriority': 'zenoss.device.priority',
        'ipAddress': 'zenoss.device.ip_address',
    }
    ZENOSS_DETAIL_NEW_TO_OLD_MAPPING = dict([(new, old) for old, new in ZENOSS_DETAIL_OLD_TO_NEW_MAPPING.iteritems()])

    COUNT_REGEX = re.compile(r'^(?P<from>\d+)?:?(?P<to>\d+)?$')

    def __init__(self, context):
        super(ZepFacade, self).__init__(context)
        config = getGlobalConfiguration()
        zep_url = config.get('zep_uri', 'http://localhost:8084')
        self.client = ZepServiceClient(zep_url)
        self.configClient = ZepConfigClient(zep_url)
        self.heartbeatClient = ZepHeartbeatClient(zep_url)
        self._guidManager = IGUIDManager(context.dmd)

    def createEventFilter(self,
        severity=(),
        status=(),
        event_class=(),
        first_seen=None,
        last_seen=None,
        status_change=None,
        update_time=None,
        count_range=None,
        element_identifier=(),
        element_sub_identifier=(),
        uuid=(),
        event_summary=None,
        tags=(),
        fingerprint=(),
        agent=(),
        monitor=(),
        current_user_name=(),
        subfilter=(),
        operator=None,
        details=None):

        filter = {}

        if uuid:
            filter['uuid'] = uuid

        if event_summary:
            if not isinstance(event_summary, (tuple, list, set)):
                event_summary = (event_summary,)
            filter['event_summary'] = map(lambda s:str(s).strip(), event_summary)

        if event_class:
            filter['event_class'] = event_class

        if status:
            filter['status'] = status

        if severity:
            filter['severity'] = severity

        if first_seen:
            filter['first_seen'] = self._timeRange(first_seen)

        if last_seen:
            filter['last_seen'] = self._timeRange(last_seen)

        if status_change:
            filter['status_change'] = self._timeRange(status_change)

        if update_time:
            filter['update_time'] = self._timeRange(update_time)

        # These tags come from params, which means for some reason someone is filtering manually on a tag.
        if tags:
            filter['tag_filter'] = {'tag_uuids': tags}

        if count_range:
            if not isinstance(count_range, (tuple, list)):
                try:
                    count = int(count_range)
                    count_range = (count, count)
                except ValueError:
                    match = ZepFacade.COUNT_REGEX.match(count_range)
                    if not match:
                        raise ValueError('Invalid range: %s' % (count_range))
                    count_range = (match.group('from'), match.group('to'))

            filter['count_range'] = {}
            count_from, count_to = count_range
            if count_from is not None:
                filter['count_range']['from'] = int(count_from)
            if count_to is not None:
                filter['count_range']['to'] = int(count_to)

        if element_identifier:
            if not isinstance(element_identifier, (tuple, list, set)):
                element_identifier = (element_identifier,)
            filter['element_identifier'] = map(lambda s:str(s).strip(), element_identifier)

        if element_sub_identifier:
            if not isinstance(element_sub_identifier, (tuple, list, set)):
                element_sub_identifier = (element_sub_identifier,)
            filter['element_sub_identifier'] = map(lambda s:str(s).strip(),
                                                   element_sub_identifier)

        if fingerprint:
            filter['fingerprint'] = fingerprint

        if agent:
            filter['agent'] = agent

        if monitor:
            filter['monitor'] = monitor

        if current_user_name:
            filter['current_user_name'] = current_user_name

        if subfilter:
            filter['subfilter'] = subfilter

        if details:
            filter['details'] = self._createEventDetailFilter(details)


        # Everything's repeated on the protobuf, so listify
        result = dict((k, listify(v)) for k,v in filter.iteritems())

        if operator:
            result['operator'] = operator

        return result

    
    def _createEventDetailFilter(self, details):
        """
        @param details: All details present in this filter request.

        Example: {
            'zenoss.device.production_state' = 4,
            'zenoss.device.priority' : 2
        }

        @type details: dict
        """
        
        detailFilterItems = []

        for key, val in details.iteritems():
            detailFilterItems.append({
               'key': key,
                'value': val,
            })
                
        log.debug('Final detail filter: %r' % detailFilterItems)
        return detailFilterItems

    def _timeRange(self, timeRange):
        d = {
            'start_time' : timeRange[0],
        }

        if len(timeRange) == 2:
            d['end_time'] = timeRange[1]

        return d

    def _getEventSort(self, sortParam):
        eventSort = {}
        if isinstance(sortParam, (list, tuple)):
            field, direction = sortParam
            eventSort['direction'] = self.SORT_DIRECTIONAL_MAP[direction.lower()]
        else:
            field = sortParam
        eventSort.update(getDetailsInfo().getSortMap()[field.lower()])
        return from_dict(EventSort, eventSort)

    def _getUserUuid(self, userName):
        # Lookup the user uuid
        user = self._dmd.ZenUsers.getUserSettings(userName)
        if user:
            return IGlobalIdentifier(user).getGUID()

    def _findUserInfo(self):
        userName = getSecurityManager().getUser().getId()
        return self._getUserUuid(userName), userName

    def addNote(self, uuid, message, userName, userUuid=None):
        if userName and not userUuid:
            userUuid = self._getUserUuid(userName)
            if not userUuid:
                raise Exception('Could not find user "%s"' % userName)

        self.client.addNote(uuid, message, userUuid, userName)

    def _getEventSummaries(self, source, offset, limit=1000):
        response, content = source(offset=offset, limit=limit)
        return {
            'total' : content.total,
            'limit' : content.limit,
            'next_offset' : content.next_offset if content.HasField('next_offset') else None,
            'events' : (to_dict(event) for event in content.events),
        }

    def getEventSummariesFromArchive(self, offset, limit=1000, sort=None, filter=None):
        return self.getEventSummaries(offset, limit, sort, filter,
                                      client_fn=self.client.getEventSummariesFromArchive)

    def getEventSummaries(self, offset, limit=1000, sort=None, filter=None, client_fn=None):
        if client_fn is None:
            client_fn = self.client.getEventSummaries
        if filter is not None and isinstance(filter,dict):
            filter = from_dict(EventFilter, filter)
        if sort is not None:
            sort = tuple(self._getEventSort(s) for s in safeTuple(sort))
        return self._getEventSummaries(source=partial(client_fn,
                                               filter=filter,
                                               sort=sort
                                               ),
                                       offset=offset, limit=limit
                                       )

    def getEventSummariesGenerator(self, filter=None, exclude=None, sort=None, archive=False):
        if exclude is not None and isinstance(exclude,dict):
            exclude = from_dict(EventFilter, exclude)
        if filter is not None and isinstance(filter,dict):
            filter = from_dict(EventFilter, filter)
        if sort is not None:
            sort = tuple(self._getEventSort(s) for s in safeTuple(sort))
        searchid = self.client.createSavedSearch(event_filter=filter, exclusion_filter=exclude, sort=sort, archive=archive)
        log.debug("created saved search %s", searchid)
        eventSearchFn = partial(self.client.savedSearch, searchid, archive=archive)
        offset = 0
        limit = 500
        try:
            while True:
                result = self._getEventSummaries(eventSearchFn, offset, limit)
                for evt in result['events']:
                    yield evt
                if result['next_offset'] is not None:
                    offset = result['next_offset']
                else:
                    break

        finally:
            try:
                log.debug("closing saved search %s", searchid)
                self.client.deleteSavedSearch(searchid, archive=archive)
            except Exception as e:
                log.debug("error closing saved search %s (%s) - %s", searchid, type(e), e)

    def getEventSummary(self, uuid):
        response, content = self.client.getEventSummary(uuid)
        return to_dict(content)

    def nextEventSummaryUpdate(self, next_request):
        status, response = self.client.nextEventSummaryUpdate(from_dict(EventSummaryUpdateRequest, next_request))
        return status, to_dict(response)

    def closeEventSummaries(self, eventFilter=None, exclusionFilter=None, limit=None):
        if eventFilter:
            eventFilter = from_dict(EventFilter, eventFilter)
        if exclusionFilter:
            exclusionFilter = from_dict(EventFilter, exclusionFilter)

        userUuid, userName = self._findUserInfo()
        status, response = self.client.closeEventSummaries(
            userUuid, userName, eventFilter, exclusionFilter, limit)
        return status, to_dict(response)

    def acknowledgeEventSummaries(self, eventFilter=None, exclusionFilter=None, limit=None):
        if eventFilter:
            eventFilter = from_dict(EventFilter, eventFilter)

        if exclusionFilter:
            exclusionFilter = from_dict(EventFilter, exclusionFilter)

        userUuid, userName = self._findUserInfo()
        status, response = self.client.acknowledgeEventSummaries(userUuid, userName, eventFilter, exclusionFilter,
                                                                 limit)
        return status, to_dict(response)

    def reopenEventSummaries(self, eventFilter=None, exclusionFilter=None, limit=None):
        if eventFilter:
            eventFilter = from_dict(EventFilter, eventFilter)
        if exclusionFilter:
            exclusionFilter = from_dict(EventFilter, exclusionFilter)

        userUuid, userName = self._findUserInfo()
        status, response = self.client.reopenEventSummaries(
            userUuid, userName, eventFilter, exclusionFilter, limit)
        return status, to_dict(response)

    def getConfig(self):
        # the config client doesn't return a ZepConfig. It merges the ZepConfig
        # with some other properties to create a config structure.
        config = self.configClient.getConfig()
        return config

    def setConfigValues(self, values):
        """
        @type  values: Dictionary
        @param values: Key Value pairs of config values
        """
        zepConfigProtobuf = from_dict(ZepConfig, values)
        self.configClient.setConfigValues(zepConfigProtobuf)

    def setConfigValue(self, name, value):
        self.configClient.setConfigValue(name, value)

    def removeConfigValue(self, name):
        self.configClient.removeConfigValue(name)
        
    def _getTopLevelOrganizerUuids(self, tagUuid):
        """
        Returns a list of child UUIDs if the specified tagUuid is a top-level
        organizer. Otherwise returns None. This is needed because several 
        operations in ZEP are performed on UUIDs tagged in the events, however
        the top-level organizers are not tagged on events as an optimization.
        
        @type  tagUuid: string
        @param tagUuid: UUID of potential top-level organizer
        """
        obj = self._guidManager.getObject(tagUuid)
        uuids = None
        if obj and obj.getDmdKey() == '/':
            uuids = [IGlobalIdentifier(n).getGUID() for n in obj.children()]
        return uuids

    def getEventSeveritiesByUuid(self, tagUuid, severities=(), status=()):
        topLevelUuids = self._getTopLevelOrganizerUuids(tagUuid)
        if topLevelUuids:
            sevmap = {}
            # Condense counts of child organizers into a flattened out count
            for uuid, sevs in self.getEventSeverities(topLevelUuids, severities=severities, status=status).iteritems():
                for sev, counts in sevs.iteritems():
                    counts_dict = sevmap.get(sev)
                    if counts_dict:
                        counts_dict['count'] += counts['count']
                        counts_dict['acknowledged_count'] += counts['acknowledged_count']
                    else:
                        sevmap[sev] = counts
            return sevmap
        
        return self.getEventSeverities(tagUuid, severities=severities, status=status)[tagUuid]

    def _createSeveritiesDict(self, eventTagSeverities):
        severities = {}
        
        for tag in eventTagSeverities:
            severities[tag.tag_uuid] = {}
            for sev in tag.severities:
                severities[tag.tag_uuid][sev.severity] = dict(count=sev.count, 
                                                              acknowledged_count=sev.acknowledged_count)
            for sev in EventSeverity.numbers:
                if not sev in severities[tag.tag_uuid]:
                    severities[tag.tag_uuid][sev] = dict(count=0, acknowledged_count=0)

        return severities

    def getEventSeverities(self, tagUuids, severities=(), status=()):
        """
        Get a dictionary of the event severity counts for each UUID.

        @param tagUuids: A sequence of element UUIDs
        @param severities: A sequence of severities to include. Default is CRITICAL/ERROR/WARNING.
        @type  severities: Sequence of severities.
        @param status: A sequence of event statuses to include. Default is NEW/ACKNOWLEDGED.
        @type  status: Sequence of event severities.
        @rtype: dict
        @return: A dictionary of UUID -> { C{EventSeverity} -> { count, acknowledged_count } }
        """
        eventTagSeverities = self._getEventTagSeverities(severity=severities, status=status, tags=tagUuids)
        return self._createSeveritiesDict(eventTagSeverities)

    def getWorstSeverityByUuid(self, tagUuid, default=SEVERITY_CLEAR, ignore=()):
        return self.getWorstSeverity([tagUuid], default=default, ignore=ignore)[tagUuid]

    def getWorstSeverity(self, tagUuids, default=SEVERITY_CLEAR, ignore=()):
        """
        Get a dictionary of the worst event severity for each UUID.

        @param tagUuids: A sequence of element UUIDs
        @param default: The default severity to use if there are no results or if a severity is ignored
        @type default: An C{EventSeverity} enum value
        @param ignore: Severities to not include as worst, use the default instead.
        @type ignore: A list of C{EventSeverity} enum values
        @rtype: dict
        @return: A dictionary of UUID -> C{EventSeverity}
        """

        # Prepopulate the list with defaults
        severities = dict.fromkeys(tagUuids, default)
        eventTagSeverities = self._getEventTagSeverities(tags=tagUuids)
        for tag in eventTagSeverities:
            for sev in tag.severities:
                if sev.severity not in ignore:
                    severities[tag.tag_uuid] = max(sev.severity, severities[tag.tag_uuid])
        return severities

    def getSeverityName(self, severity):
        return EventSeverity.getPrettyName(severity)

    def createEventMapping(self, evdata, eventClassId):
        """
        Associates event(s) with an event class.
        """
        evmap = None
        evclass = self._dmd.Events.getOrganizer(eventClassId)
        numCreated = 0
        numNotUnknown = 0
        numNoKey = 0

        for data in evdata:
            evclasskey = data.get('eventClassKey')
            if data.get('eventClass'):
                curevclass = data.get('eventClass')['text']
            else:
                curevclass = Unknown
            example = data.get('message')
            if curevclass != Unknown:
                numNotUnknown += 1
                continue
            if not evclasskey:
                numNoKey += 1
                continue
            evmap = evclass.createInstance(evclasskey)
            evmap.eventClassKey = evclasskey
            evmap.example = example
            evmap.index_object()
            numCreated += 1
        # message
        msg = ''
        if numNotUnknown:
            msg += ((msg and ' ') +
                    '%s event%s %s not of the class Unknown.' % (
                        numNotUnknown,
                        (numNotUnknown != 1 and 's') or '',
                        (numNotUnknown != 1 and 'are') or 'is'))
        if numNoKey:
            msg += ((msg and ' ') +
                    '%s event%s %s not have an event class key.' % (
                        numNoKey,
                        (numNoKey != 1 and 's') or '',
                        (numNoKey != 1 and 'do') or 'does'))
        msg += (msg and ' ') + 'Created %s event mapping%s.' % (
                        numCreated,
                        (numCreated != 1 and 's') or '')
        # redirect
        url = None
        if len(evdata) == 1 and evmap:
            url = evmap.absolute_url()
        elif evclass and evmap:
            url = evclass.absolute_url()
        return msg, url

    def _getEventTagSeverities(self, eventClass=(), severity=(), status=(), tags=()):
        if not severity:
            severity = (SEVERITY_CRITICAL, SEVERITY_ERROR, SEVERITY_WARNING)
        if not status:
            status = (STATUS_NEW, STATUS_ACKNOWLEDGED)
        eventFilter = self.createEventFilter(
            severity=severity,
            status=status,
            event_class=eventClass,
            tags=tags,
            )

        response, content = self.client.getEventTagSeverities(from_dict(EventFilter, eventFilter))
        return content.severities

    def getDevicePingIssues(self):
        return self.getDeviceIssues(eventClass=[Status_Ping],
                                    severity=[SEVERITY_WARNING,SEVERITY_ERROR,SEVERITY_CRITICAL],
                                    status=[STATUS_NEW,STATUS_ACKNOWLEDGED,STATUS_SUPPRESSED])

    def getDeviceStatusIssues(self):
        return self.getDeviceIssues(eventClass=["/Status/"],
                                    severity=[SEVERITY_ERROR,SEVERITY_CRITICAL],
                                    status=[STATUS_NEW,STATUS_ACKNOWLEDGED])

    def getDeviceIssues(self, eventClass=(),
                        severity=(SEVERITY_DEBUG, SEVERITY_INFO, SEVERITY_WARNING, SEVERITY_ERROR, SEVERITY_CRITICAL),
                        status=(STATUS_NEW,)):
        tagSeverities = self._getEventTagSeverities(eventClass, severity, status)
        issues = []
        for eventTagSeverity in tagSeverities:
            device = self._guidManager.getObject(eventTagSeverity.tag_uuid)
            if device and isinstance(device, Device):
                count = 0
                for severity in eventTagSeverity.severities:
                    count += severity.count
                total = eventTagSeverity.total
                issues.append((device.id, count, total))
        return issues

    def getDeviceIssuesDict(self, eventClass=(), severity=(), status=()):
        severities = self._getEventTagSeverities(eventClass, severity, status)
        return self._createSeveritiesDict(severities)

    def getDetails(self):
        """
        Retrieve all of the indexed detail items.

        @rtype list of EventDetailItem dicts
        """
        return getDetailsInfo().getDetails()

    def getUnmappedDetails(self):
        """
        Return only non-zenoss details. This is used to get details that will not be mapped to another key.
        (zenoss.device.production_state maps back to prodState, so will be excluded here)
        """
        return getDetailsInfo().getUnmappedDetails()

    def getDetailsMap(self):
        """
        Return a mapping of detail keys to dicts of detail items
        """
        return getDetailsInfo().getDetailsMap()

    def parseParameterDetails(self, parameters):
        """
        Given grid parameters, split into keys that are details and keys that are other parameters.
        """

        params = {}
        details = {}

        detail_keys = self.getDetailsMap().keys()
        for k, v in parameters.iteritems():

            if k in self.ZENOSS_DETAIL_OLD_TO_NEW_MAPPING:
                k = self.ZENOSS_DETAIL_OLD_TO_NEW_MAPPING[k]
                
            if k in detail_keys:
                details[k] = v
            else:
                params[k] = v

        return params, details


    def addIndexedDetails(self, detailItemSet):
        """
        @type detailItemSet: zenoss.protocols.protobufs.zep_pb2.EventDetailItemSet
        """
        return self.configClient.addIndexedDetails(detailItemSet)

    def updateIndexedDetail(self, item):
        """
        @type item: zenoss.protocols.protobufs.zep_pb2.EventDetailItem
        """
        return self.configClient.updateIndexedDetail(item)
    
    def removeIndexedDetail(self, key):
        """
        @type key: string
        """
        return self.configClient.removeIndexedDetail(key)

    def countEventsSince(self, since):
        """
        Returns the total number of events in summary and archive that have been
        seen since the specified time (in seconds).

        @type  since: int
        @param since: Time (in seconds) from the epoch.
        @rtype:       int
        @return:      The number of events in summary and archive that have been seen
                      since the specified time.
        """
        sinceInMillis = int(since * 1000)
        eventFilter = self.createEventFilter(last_seen=[sinceInMillis])
        total = self.getEventSummaries(0, filter=eventFilter, limit=0)['total']
        total += self.getEventSummariesFromArchive(0, filter=eventFilter, limit=0)['total']
        return total

    def getHeartbeats(self, monitor=None):
        response, heartbeats = self.heartbeatClient.getHeartbeats(monitor=monitor)
        heartbeats_dict = to_dict(heartbeats)
        return heartbeats_dict.get('heartbeats', [])

    def deleteHeartbeats(self, monitor=None):
        self.heartbeatClient.deleteHeartbeats(monitor=monitor)

class ZepDetailsInfo:
    """
    Contains information about the indexed event details on ZEP.
    """

    def __init__(self):
        config = getGlobalConfiguration()
        zep_url = config.get('zep_uri', 'http://localhost:8084')
        self._configClient = ZepConfigClient(zep_url)
        self._initialized = False

    def _initDetails(self):
        self._sortMap = dict(ZepFacade.DEFAULT_SORT_MAP)
        response, content = self._configClient.getDetails()

        detailsResponseDict = to_dict(content)
        self._details = detailsResponseDict.get('details', [])
        self._unmappedDetails = []
        self._detailsMap = {}
        for detail_item in self._details:
            detailKey = detail_item['key']
            sortField = { 'field': EventSort.DETAIL, 'detail_key': detailKey }
            mappedName = ZepFacade.ZENOSS_DETAIL_NEW_TO_OLD_MAPPING.get(detailKey, None)
            # If we have a mapped name, add it to the sort map to support sorting using old or new names
            if mappedName:
                self._sortMap[mappedName.lower()] = sortField
            else:
                self._unmappedDetails.append(detail_item)
            self._sortMap[detailKey.lower()] = sortField
            self._detailsMap[detailKey] = detail_item
        self._initialized = True

    def reload(self):
        """
        Reloads the event details configuration from ZEP.
        """
        self._initialized = False
        self._initDetails()

    def getDetails(self):
        """
        Retrieve all of the indexed detail items.

        @rtype list of EventDetailItem dicts
        """
        if not self._initialized:
            self._initDetails()
        return self._details

    def getUnmappedDetails(self):
        """
        Return only non-zenoss details. This is used to get details that will not be mapped to another key.
        (zenoss.device.production_state maps back to prodState, so will be excluded here)
        """
        if not self._initialized:
            self._initDetails()
        return self._unmappedDetails

    def getDetailsMap(self):
        """
        Return a mapping of detail keys to dicts of detail items
        """
        if not self._initialized:
            self._initDetails()
        return self._detailsMap

    def getSortMap(self):
        """
        Returns a mapping of a lowercase event field name to a dictionary which can be used
        to build the EventSort object to pass to ZEP.
        """
        if not self._initialized:
            self._initDetails()
        return self._sortMap

# Lazy-loaded cache of event details from ZEP
_ZEP_DETAILS_INFO = []
def getDetailsInfo():
    if not _ZEP_DETAILS_INFO:
        _ZEP_DETAILS_INFO.append(ZepDetailsInfo())
    return _ZEP_DETAILS_INFO[0]
