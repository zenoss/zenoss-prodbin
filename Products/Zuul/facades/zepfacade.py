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
from zope.interface import implements
from zope.component import getUtility
from Products.Zuul.facades import ZuulFacade
from Products.Zuul.interfaces import IZepFacade
import pkg_resources
from zenoss.protocols.services.zep import ZepServiceClient, EventSeverity, EventStatus
from zenoss.protocols.jsonformat import to_dict, from_dict
from zenoss.protocols.protobufs.zep_pb2 import EventSummaryFilter, EventSummary, Event, NumberCondition
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier

log = logging.getLogger(__name__)

class ZepFacade(ZuulFacade):
    implements(IZepFacade)

    _opMap = {
        '<' : NumberCondition.LT,
        '>' : NumberCondition.GT,
        '>=' : NumberCondition.GTEQ,
        '<=' : NumberCondition.LTEQ,
        '=' : NumberCondition.EQ,
        None : NumberCondition.EQ,
    }

    def __init__(self, context):
        super(ZepFacade, self).__init__(context)

        config = getGlobalConfiguration()

        self.client = ZepServiceClient(config.get('zep_uri', 'http://localhost:8084'))

    def createFilter(self,
        uuid=[],
        summary=None,
        event_class=None,
        status=[],
        severity=[],
        first_seen=None,
        last_seen=None,
        status_change=None,
        tags=[],
        count=None,
        element_identifier=None,
        element_sub_identifier=None):
        filter = {}

        if uuid:
            filter['uuid'] = uuid

        if summary:
            filter['event_summary'] = str(summary).strip()

        if event_class:
            filter['event_class'] = str(event_class).strip()

        if status:
            filter['status'] = status

        if severity:
            filter['severity'] = severity

        if first_seen:
            filter['first_seen'] = first_seen

        if last_seen:
            filter['last_seen'] = last_seen

        if status_change:
            filter['status_change'] = status_change

        if tags:
            filter['tag_uuids'] = tags

        if count:
            filter['count'] = count

        if element_identifier:
            filter['element_identifier'] = str(element_identifier).strip()

        if element_sub_identifier:
            filter['element_sub_identifier'] = str(element_sub_identifier).strip()

        return filter

    def _timeRange(self, timeRange):
        d = {
            'start_time' : timeRange[0],
        }

        if len(timeRange) == 2:
            d['end_time'] = timeRange[1]

        return d

    def getEventSummaries(self, offset, limit=100, keys=None, sort=None, filter={}):
        filterBuf = None
        if filter:
            # Build protobuf filter
            if 'count' in filter:
                m = re.match(r'^(?P<op>>|<|=|>=|<=)?(?P<num>[0-9]+)$', filter['count'])
                if m:
                    filter['count'] = {
                        'op' : self._opMap[m.groupdict()['op']],
                        'value' : int(m.groupdict()['num']),
                    }
                else:
                    raise Exception('Invalid count filter %s' % filter['count'])

            if 'first_seen' in filter:
                filter['first_seen'] = self._timeRange(filter['first_seen'])

            if 'last_seen' in filter:
                filter['last_seen'] = self._timeRange(filter['last_seen'])

            filterBuf = from_dict(EventSummaryFilter, filter)

        response, content = self.client.getEventSummaries(offset=offset, limit=limit, keys=keys, sort=sort, filter=filterBuf)
        return {
            'total' : content.total,
            'events' : (to_dict(event) for event in content.events),
        }

    def _getUserUuid(self, userName):
        # Lookup the user uuid
        user = self._dmd.ZenUsers.getUserSettings(userName)
        if user:
            return IGlobalIdentifier(user).getGUID()

    def getEventSummary(self, uuid):
        response, content = self.client.getEventSummary(uuid)
        return to_dict(content)

    def addNote(self, uuid, message, userName, userUuid=None):
        if userName and not userUuid:
            userUuid = self._getUserUuid(userName)
            if not userUuid:
                raise Exception('Could not find user "%s"' % userName)

        self.client.addNote(uuid, message, userUuid, userName)

    def closeEventSummary(self, uuid):
        return self.client.closeEventSummary(uuid)

    def acknowledgeEventSummary(self, uuid, userName=None, userUuid=None):
        if userName and not userUuid:
            userUuid = self._getUserUuid(userName)
            if not userUuid:
                raise Exception('Could not find user "%s"' % userName)

        return self.client.acknowledgeEventSummary(uuid, userUuid)

    def reopenEventSummary(self, uuid):
        return self.client.reopenEventSummary(uuid)
