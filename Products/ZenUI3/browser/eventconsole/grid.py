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

from Products.ZenUtils.jsonutils import JavaScript, javascript
from Products.ZenUI3.utils.javascript import JavaScriptSnippet
from Products.ZenUI3.browser.eventconsole.columns import COLUMN_CONFIG, ARCHIVE_COLUMN_CONFIG, DEFAULT_COLUMN_ORDER, DEFAULT_COLUMNS

class EventConsoleView(BrowserView):
    __call__ = ViewPageTemplateFile('view-events.pt')


class HistoryConsoleView(BrowserView):
    __call__ = ViewPageTemplateFile('view-history-events.pt')


def column_config(request=None, archive=False):
    columns = COLUMN_CONFIG
    if archive:
        columns = ARCHIVE_COLUMN_CONFIG

    defs = []
    for field in DEFAULT_COLUMN_ORDER:
        col = columns[field].copy()
        if request:
            msg = _(col['header'])
            col['header'] = zope.i18n.translate(msg, context=request)
        col['id'] = field
        col['dataIndex'] = field
        if isinstance(col['filter'], basestring):
            col['filter'] = {'xtype':col['filter']}
        col['sortable'] = col.get('sortable', False)
        col['hidden'] = col.get('hidden', field not in DEFAULT_COLUMNS)

        if 'renderer' in col:
            col['renderer'] = JavaScript(col['renderer'])

        s = javascript(col)
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
        """ % paths


class GridColumnDefinitions(JavaScriptSnippet):

    def snippet(self):
        last_path_item = self.request['PATH_INFO'].split('/')[-1]
        archive = last_path_item.lower().find('history') != -1 or last_path_item.lower().find('archive') != -1

        result = ["Ext.onReady(function(){"]

        defs = column_config(self.request, archive=archive)
        result.append('Zenoss.env.COLUMN_DEFINITIONS=[')
        result.append(',\n'.join(defs))
        result.append('];')

        result.append("Zenoss.env.EVENT_AUTO_EXPAND_COLUMN='summary';")

        result.append('});')

        return '\n'.join(result)
