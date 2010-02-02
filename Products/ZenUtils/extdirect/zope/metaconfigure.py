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
import zope.component
from zope.interface import Interface
from zope.viewlet.metaconfigure import viewletDirective
from zope.publisher.interfaces.browser import IBrowserView
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from zope.viewlet.viewlet import ViewletBase
try:
    from Products.Five.browser.metaconfigure import page
except ImportError:
    from zope.app.publisher.browser.viewmeta import page

from Products.ZenUtils.extdirect.router import DirectProviderDefinition

from interfaces import IExtDirectJavaScriptManager

class SourceViewletBase(ViewletBase):
    _source = ""
    weight=0
    def render(self):
        return self._source

def JavaScriptSourceViewlet(source):
    klass = type('JavaScriptSourceViewlet',
                 (SourceViewletBase,),
                 {'_source':source,
                  'weight':2})
    return klass

def directRouter(_context, name, class_, namespace=None, for_=Interface,
                 layer=IDefaultBrowserLayer, timeout="30000"):

    # Register the view at which the class will be available
    page(_context, name, 'zope.Public', for_, layer, class_=class_)

    # Make a viewlet class with the appropriate javascript source
    source = DirectProviderDefinition(class_, name, timeout, namespace).render()
    viewletclass = JavaScriptSourceViewlet(source)

    viewletDirective(_context, name, 'zope.Public', for_, layer,
                     manager=IExtDirectJavaScriptManager, class_=viewletclass)
