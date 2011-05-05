###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

class ExtDirectJsView(BrowserView):
    template = ViewPageTemplateFile('extdirect.js.pt')

    def __call__(self, *args, **kwargs):
        self.request.response.enableHTTPCompression(REQUEST=self.request)
        self.request.response.setHeader('Content-Type', 'text/javascript')
        return self.template()
