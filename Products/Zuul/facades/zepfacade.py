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
        summary=None,
        event_class=None,
        status=None,
        severity=None,
        first_time=None,
        last_time=None,
        tags=None,
        count=None,
        element_identifier=None,
        element_sub_identifier=None):
        filter = {}

        if summary:
            filter['summary'] = summary

        if event_class:
            filter['event_class'] = event_class

        if status:
            filter['status'] = status

        if severity:
            filter['severity'] = severity

        if first_time:
            filter['first_time'] = first_time

        if last_time:
            filter['last_time'] = last_time

        if tags:
            filter['tag_uuids'] = tags

        if count:
            filter['count'] = count

        if element_identifier:
            filter['element_identifier'] = element_identifier

        if element_sub_identifier:
            filter['element_sub_identifier'] = element_sub_identifier

        return filter

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

            filterBuf = from_dict(EventSummaryFilter, filter)

        response, content = self.client.getEventSummaries(offset=offset, limit=limit, keys=keys, sort=sort, filter=filterBuf)
        return {
            'total' : content.total,
            'events' : (to_dict(event) for event in content.events),
        }

    def getEventSummary(self, uuid):
        response, content = self.client.getEventSummary(uuid)
        return to_dict(content)
