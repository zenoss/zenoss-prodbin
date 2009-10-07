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
from Products.Five.browser import BrowserView

class ExtJSShortcut(BrowserView):
    def __getitem__(self, name):
        return self.context.unrestrictedTraverse('++resource++extjs')[name]

class ZenUIResourcesShortcut(BrowserView):
    def __getitem__(self, name):
        return self.context.unrestrictedTraverse('++resource++zenui')[name]
