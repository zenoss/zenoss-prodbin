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
from zope.component import queryUtility

import zope.i18n
from zope.i18nmessageid import MessageFactory
_ = MessageFactory('zenoss')

from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from Products.ZenUtils.json import json
from Products.ZenUI3.utils.javascript import JavaScriptSnippet
from Products.ZenUI3.browser.eventconsole.columns import COLUMN_CONFIG
from Products.Zuul.interfaces import IEventFacade


class EventConsoleView(BrowserView):
    __call__ = ViewPageTemplateFile('console.pt')
    # Need an id so the tabs can tell what's going on
    __call__.id = 'viewEvents'


class HistoryConsoleView(BrowserView):
    __call__ = ViewPageTemplateFile('historyconsole.pt')
    # Need an id so the tabs can tell what's going on
    __call__.id = 'viewHistoryEvents'


def column_config(fields, request=None):
    defs = []
    for field in fields:
        col = COLUMN_CONFIG[field].copy()
        if request:
            msg = _(col['header'])
            col['header'] = zope.i18n.translate(msg, context=request)
        col['id'] = field
        col['dataIndex'] = field
        if isinstance(col['filter'], basestring):
            col['filter'] = {'xtype':col['filter']}
        col['sortable'] = True
        renderer = None
        if 'renderer' in col:
            renderer = col['renderer']
            del col['renderer']
        s = json(col)
        if renderer:
            ss, se = s[:-1], s[-1]
            s = ''.join([ss, ',renderer:', renderer, se])
        defs.append(s)
    return defs


class EventClasses(JavaScriptSnippet):
    def snippet(self):
        orgs = self.context.dmd.Events.getSubOrganizers()
        paths = ['/'.join(x.getPrimaryPath()) for x in orgs]
        paths = [p.replace('/zport/dmd/Events','') for p in paths]
        paths.sort()
        return """
        Ext.onReady(function(){
            Zenoss.env.EVENT_CLASSES = %s;
        })
        """ % paths;


class GridColumnDefinitions(JavaScriptSnippet):

    def snippet(self):
        api = queryUtility(IEventFacade)
        result = ["Ext.onReady(function(){Zenoss.env.COLUMN_DEFINITIONS=["]
        defs = column_config(api.fields(self.context), self.request)
        result.append(',\n'.join(defs))
        result.append(']});')
        result = '\n'.join(result)
        return result







