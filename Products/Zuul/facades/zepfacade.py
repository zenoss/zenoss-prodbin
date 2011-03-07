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

import logging
import re
from AccessControl import getSecurityManager
from zope.interface import implements
from Products.Zuul.facades import ZuulFacade
from Products.Zuul.interfaces import IZepFacade
from Products.ZenEvents.ZenEventClasses import Unknown

import pkg_resources
from zenoss.protocols.services.zep import ZepServiceClient, EventSeverity, ZepConfigClient
from zenoss.protocols.jsonformat import to_dict, from_dict
from zenoss.protocols.protobufs.zep_pb2 import EventSort, EventFilter, EventSummaryUpdateRequest, ZepConfig
from zenoss.protocols.protobufutil import listify
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from zenoss.protocols.protobufs.zep_pb2 import SEVERITY_CLEAR, SEVERITY_CRITICAL, SEVERITY_ERROR,\
     STATUS_NEW, STATUS_ACKNOWLEDGED, OR, AND


log = logging.getLogger(__name__)

class ZepFacade(ZuulFacade):
    implements(IZepFacade)

    AND = AND
    OR = OR

    SORT_MAP = {
        'eventstate':  { 'field': EventSort.STATUS },
        'severity':    { 'field': EventSort.SEVERITY },
        'firsttime':   { 'field': EventSort.FIRST_SEEN },
        'lasttime':    { 'field': EventSort.LAST_SEEN },
        'eventclass':  { 'field': EventSort.EVENT_CLASS },
        'device':      { 'field': EventSort.ELEMENT_IDENTIFIER },
        'component':   { 'field': EventSort.ELEMENT_SUB_IDENTIFIER },
        'count':       { 'field': EventSort.COUNT },
        'summary':     { 'field': EventSort.EVENT_SUMMARY },
        'ownerid':     { 'field': EventSort.ACKNOWLEDGED_BY_USER_NAME },
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
        'prodState' : 'zenoss.device.production_state',
        'DevicePriority' : 'zenoss.device.priority',
    }
    ZENOSS_DETAIL_NEW_TO_OLD_MAPPING = dict([(new, old) for old, new in ZENOSS_DETAIL_OLD_TO_NEW_MAPPING.iteritems()])

    COUNT_REGEX = re.compile(r'^(?P<from>\d+)?:?(?P<to>\d+)?$')

    def __init__(self, context):
        super(ZepFacade, self).__init__(context)
        self._sortMap = {}
        self._sortMap.update(ZepFacade.SORT_MAP)
        config = getGlobalConfiguration()
        zep_url = config.get('zep_uri', 'http://localhost:8084')
        self.client = ZepServiceClient(zep_url)
        self.configClient = ZepConfigClient(zep_url)
        self.initDetails()

    def createEventFilter(self,
        severity=(),
        status=(),
        event_class=(),
        first_seen=None,
        last_seen=None,
        status_change=None,
        count_range=None,
        element_identifier=(),
        element_sub_identifier=(),
        uuid=(),
        event_summary=None,
        tags=(),
        fingerprint=(),
        agent=(),
        monitor=(),
        acknowledged_by_user_name=(),
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
            filter['status_change'] = status_change

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

        if acknowledged_by_user_name:
            filter['acknowledged_by_user_name'] = acknowledged_by_user_name

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
        eventSort.update(self._sortMap[field.lower()])
        return from_dict(EventSort, eventSort)

    def _getEventSummaries(self, source, offset, limit=100, keys=None, sort=None, filter=None):
        filterBuf = None

        if filter:
            filterBuf = from_dict(EventFilter, filter)
        
        eventSort = None
        if sort:
            if isinstance(sort, (list, tuple)):
                # Multiple sort fields
                if isinstance(sort[0], (list,tuple)):
                    eventSort = [self._getEventSort(s) for s in sort]
                else:
                    eventSort = self._getEventSort(sort)
            else:
                eventSort = self._getEventSort(sort)

        response, content = source(offset=offset, limit=limit, keys=keys, sort=eventSort, filter=filterBuf)
        return {
            'total' : content.total,
            'limit' : content.limit,
            'next_offset' : content.next_offset,
            'events' : (to_dict(event) for event in content.events),
        }

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

    def getEventSummariesFromArchive(self, offset, limit=100, sort=None, filter=None):
        return self._getEventSummaries(self.client.getEventSummariesFromArchive, offset=offset, limit=limit, sort=sort,
                                       filter=filter)

    def getEventSummaries(self, offset, limit=100, sort=None, filter=None):
        return self._getEventSummaries(self.client.getEventSummaries, offset=offset, limit=limit, sort=sort,
                                       filter=filter)

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

    def getEventSeveritiesByUuid(self, tagUuid):
        return self.getEventSeverities([tagUuid])[tagUuid]

    def _createSeveritiesDict(self, content, tagUuids):
        if content:
            # Pre-populate the list with count = 0 to make sure all tags request exist in the result
            severities = dict.fromkeys(tagUuids, dict.fromkeys(EventSeverity.numbers, 0))
            for tag in content.severities:
                # Since every element is using a shared default dict we can't just updated it, we
                # have to create a new copy, otherwise we are just updating the same dict.
                severities[tag.tag_uuid] = dict.fromkeys(EventSeverity.numbers, 0)
                severities[tag.tag_uuid].update((sev.severity, sev.count) for sev in tag.severities)

            return severities

    def getEventSeverities(self, tagUuids):
        """
        Get a dictionary of the event severity counds for each UUID.

        @param tagUuids: A sequence of element UUIDs
        @rtype: dict
        @return: A dictionary of UUID -> { C{EventSeverity} -> count }
        """
        response, content = self.client.getEventSeverities(tagUuids)
        return self._createSeveritiesDict(content, tagUuids)

    def getWorstSeverityByUuid(self, tagUuid, default=SEVERITY_CLEAR, ignore=None):
        return self.getWorstSeverity([tagUuid], default=default, ignore=ignore)[tagUuid]

    def getWorstSeverity(self, tagUuids, default=SEVERITY_CLEAR, ignore=None):
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
        response, content = self.client.getWorstSeverity(tagUuids)
        if content:
            for tag in content.severities:
                sev = tag.severities[0].severity
                severities[tag.tag_uuid] = default if ignore and sev in ignore else sev

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

    def getDeviceIssues(self):
        """
        Returns the same data structure as getEventSeverities, but this
        will return it for all devices that have issues with severity > Error and
        a status of new or acknowledged.
        """
        filters = self.createEventFilter(
            severity=[SEVERITY_CRITICAL, SEVERITY_ERROR],
            status=[STATUS_NEW, STATUS_ACKNOWLEDGED]
            )

        response, content = self.client.getDeviceIssues(from_dict(EventFilter, filters))
        if content:
            uuids = [severities.tag_uuid for severities in content.severities]
            return self._createSeveritiesDict(content, uuids)


    def initDetails(self):
        response, content = self.configClient.getDetails()

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

    def getDetails(self):
        """
        Retrieve all of the indexed detail items.

        @rtype list of EventDetailItem dicts
        """
        return self._details

    def getUnmappedDetails(self):
        """
        Return only non-zenoss details. This is used to get details that will not be mapped to another key.
        (zenoss.device.production_state maps back to prodState, so will be excluded here)
        """
        return self._unmappedDetails

    def getDetailsMap(self):
        """
        Return a mapping of detail keys to dicts of detail items
        """
        return self._detailsMap

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
