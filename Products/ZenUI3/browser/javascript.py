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
import Globals
import zope.interface

from interfaces import IMainSnippetManager
from Products.ZenUI3.utils.javascript import JavaScriptSnippetManager,\
    JavaScriptSnippet, SCRIPT_TAG_TEMPLATE
from Products.ZenUI3.browser.interfaces import IJavaScriptSrcViewlet,\
    IJavaScriptBundleViewlet, IJavaScriptSrcManager
from Products.Five.viewlet.viewlet import ViewletBase
from Products.ZenUI3.navigation.manager import WeightOrderedViewletManager

SCRIPT_TAG_SRC_TEMPLATE = '<script type="text/javascript" src="%s"></script>\n'

class MainSnippetManager(JavaScriptSnippetManager):
    """
    A viewlet manager to handle Ext.Direct API definitions.
    """
    zope.interface.implements(IMainSnippetManager)

class JavaScriptSrcManager(WeightOrderedViewletManager):
    zope.interface.implements(IJavaScriptSrcManager)
    
class JavaScriptSrcViewlet(ViewletBase):
    zope.interface.implements(IJavaScriptSrcViewlet)
    path = None

    def render(self):
        val = None
        if self.path:
            val = SCRIPT_TAG_SRC_TEMPLATE % self.path
        return val

class JavaScriptSrcBundleViewlet(ViewletBase):
    zope.interface.implements(IJavaScriptBundleViewlet)
    #space delimited string of src paths
    paths = ''
    def render(self):
        vals = []
        if self.paths:
            for path in self.paths.split():
                vals.append(SCRIPT_TAG_SRC_TEMPLATE % path)
        js = ''
        if vals:
            js = "".join(vals)
        return js
    
class ExtBaseJs(JavaScriptSrcViewlet):
    zope.interface.implements(IJavaScriptSrcViewlet)
    def update(self):
        if Globals.DevelopmentMode:
            self.path = "/++resource++extjs/adapters/ext/ext-base-debug.js"
        else:
            self.path = "/++resource++extjs/adapters/ext/ext-base.js"

class ExtAllJs(JavaScriptSrcViewlet):
    zope.interface.implements(IJavaScriptSrcViewlet)
    path = None
    def update(self):
        if Globals.DevelopmentMode:
            self.path = "/++resource++extjs/ext-all-debug.js"
        else:
            self.path = "/++resource++extjs/ext-all.js"

class LiveGridJs(JavaScriptSrcViewlet):
    zope.interface.implements(IJavaScriptSrcViewlet)
    def update(self):
        if Globals.DevelopmentMode:
            self.path = "/++resource++zenui/js/livegrid/livegrid-all-debug.js"
        else:
            self.path = "/++resource++zenui/js/livegrid/livegrid-all.js"

class FireFoxExtCompat(JavaScriptSnippet):
    def snippet(self):
        js ="""
         (function() {
            var ua = navigator.userAgent.toLowerCase();
            if (ua.indexOf("firefox/3.6") > -1) {
                Ext.toArray = function(a, i, j, res) {
                    res = [];
                    Ext.each(a, function(v) { res.push(v); });
                    return res.slice(i || 0, j || res.length);
                }
            }
        })();
        """
        return  SCRIPT_TAG_TEMPLATE% js
