##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.ZenUtils.extdirect.router import DirectRouter

class ZopeDirectRouter(DirectRouter):
    def __init__(self, context, request=None):
        self.context = context
        self.request = request

    def __call__(self):
        body = self.request.get('BODY')
        self.request.response.setHeader('Content-Type', 'application/json')
        self.request.response.enableHTTPCompression(self.request)
        return super(ZopeDirectRouter, self).__call__(body)
