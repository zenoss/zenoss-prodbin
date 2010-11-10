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
import uuid
from zope.interface import implements
from zope.component import getUtility
from Products.Zuul.facades import ZuulFacade
from Products.Zuul.interfaces import IZepFacade
import pkg_resources
from zenoss.protocols.services.zep import ZepServiceClient
from zenoss.protocols.jsonformat import to_dict
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration

log = logging.getLogger(__name__)


class ZepFacade(ZuulFacade):
    implements(IZepFacade)

    def __init__(self, context):
        super(ZepFacade, self).__init__(context)

        config = getGlobalConfiguration()

        self.client = ZepServiceClient(config.get('zep_uri', 'http://localhost:8084'))

    def getEventSummaries(self, offset, limit=100, keys=None, sort=None, filter={}):
        response, content = self.client.getEventSummaries(offset, limit, keys, sort)
        return {
            'total' : len(content.events),
            'events' : (to_dict(event) for event in content.events),
        }

    def getEventSummary(self, uuid):
        response, content = self.client.getEventSummary(uuid)
        return to_dict(content)
