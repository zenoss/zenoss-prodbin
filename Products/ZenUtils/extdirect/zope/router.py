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
from Products.ZenUtils.extdirect.router import DirectRouter

class ZopeDirectRouter(DirectRouter):
    def __init__(self, context, request=None):
        self.context = context
        self.request = request

    def __call__(self):
        try:
            # Zope 3
            body = self.request.bodyStream.getCacheStream().getvalue()
        except AttributeError:
            # Zope 2
            body = self.request.get('BODY')
        self.request.response.setHeader('Content-Type', 'application/json')
        return super(ZopeDirectRouter, self).__call__(body)
