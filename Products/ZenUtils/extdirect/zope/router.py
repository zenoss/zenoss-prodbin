##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

import cgi
from AccessControl import getSecurityManager
from Products.ZenUtils.extdirect.router import DirectRouter, DirectException
from Products.ZenModel.UserSettings import UserSettings
from Products.ZenModel.ZenossSecurity import (
    ZEN_MANAGER_ROLE, CZ_ADMIN_ROLE, MANAGER_ROLE
)
from zExceptions import NotFound


class ZopeDirectRouter(DirectRouter):
    def __init__(self, context, request=None):
        self.context = context
        self.request = request

    def __call__(self):
        if isinstance(getattr(self.request, 'PARENTS')[0], UserSettings):
            currentUser = getSecurityManager().getUser()
            if not(
                currentUser.has_role(MANAGER_ROLE) or
                currentUser.has_role(CZ_ADMIN_ROLE) or
                currentUser.has_role(ZEN_MANAGER_ROLE) or
                currentUser._id == self.request.PARENTS[0].id
            ):
                raise NotFound(self.request.URL)

        # Allow only requests with application/json content type as text/plain
        # content type is used for CSRF attacks.
        content_type = self.request.get_header('content-type')
        mimetype, options = cgi.parse_header(content_type)
        if mimetype.lower() != "application/json":
            raise DirectException(
                "Only 'application/json' is supported as content type.")

        body = self.request.get('BODY')
        self.request.response.setHeader('Content-Type', 'application/json')
        self.request.response.enableHTTPCompression(self.request)
        return super(ZopeDirectRouter, self).__call__(body)
