###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import urllib
from Products.Five.browser import BrowserView
from Products.ZenUtils.json import json
from Products.ZenUtils.Utils import unused, formreq


class EventConsole(BrowserView):
    """
    A view for Devices, CustomEventViews and EventViews that provides JSON data
    to populate the event console widget.
    """
    def __call__(self, **kwargs):
        return self._getEventsData(**kwargs)

    @json
    @formreq
    def _getEventsData(self, offset=0, count=50, getTotalCount=True, 
                       startdate=None, enddate=None, filter='', severity=2,
                       state=1, orderby='', **kwargs):
        """
        Data that populates the event console.

        @return: A JSON representation of a tuple containing a list of lists of
        event info, and the total number of matching events
        @rtype: "([[a, b, c], [a, b, c]], 17)"
        """
        unused(kwargs)

        context = self.context
        zem = self._getEventManager()

        if hasattr(context, 'getResultFields'):
            fields = context.getResultFields()
        else:
            # Use default result fields
            if hasattr(context, 'event_key'):
                base = context
            else:
                base = zem.dmd.Events
            fields = zem.lookupManagedEntityResultFields(base.event_key)

        data, totalCount = zem.getEventListME(context,
            offset=offset, rows=count, resultFields=fields,
            getTotalCount=getTotalCount, filter=filter, severity=severity,
            state=state, orderby=orderby, startdate=startdate, enddate=enddate)

        results = [self._extract_data_from_zevent(ev, fields) for ev in data]
        return (results, totalCount)

    def _getEventManager(self):
        return self.context.dmd.ZenEventManager

    def _extract_data_from_zevent(self, zevent, fields):
        """return a list of data elements that map to the fields parameter.
        """
        def _sanitize(val):
            return val.replace('<', '&lt;').replace('>','&gt;')

        from Products.ZenModel.Device import Device
        contextIsDevice = isinstance( self.context, Device )
        #import pdb;pdb.set_trace()
        data = []
        for field in fields:
            value = getattr(zevent, field)
            _shortvalue = str(value) or ''
            if field == "device":
                dev = self.context.dmd.searchDevices( value )
                if len(dev) == 1:
                    devUrl = '%s/viewEvents' % dev[0].getPrimaryUrlPath()
                    value = dev[0].urlLink(url=devUrl)
                else:
                    value = urllib.quote('<a class="%s"' % ('') +
                            ' href="/zport/dmd/deviceSearchResults'
                            '?query=%s">%s</a>' % (value, _shortvalue))
            elif field == 'eventClass':
                _shortvalue = _shortvalue.replace('/','/&shy;')
                if not zevent.eventPermission: 
                    value = _shortvalue
                else:
                    value = urllib.quote('<a class="%s" ' % ('') +
                      'href="/zport/dmd/Events%s">%s</a>' % (value,_shortvalue))
            elif field == 'component' and ( getattr(zevent, 'device', None) or
                                            contextIsDevice ):
                #import pdb;pdb.set_trace()
                component = getattr(zevent, 'component')
                if contextIsDevice:
                    device = self.context.id
                else:
                    device = getattr(zevent,'device')

                comp = self.context.dmd.searchComponents( device, component )
                if len(comp) == 1:
                    compUrl = '%s/viewEvents' % comp[0].getPrimaryUrlPath()
                    value = comp[0].urlLink(url=compUrl)
                else:
                    value = urllib.quote('<a class="%s"' % ('') +
                            ' href="/zport/dmd/searchComponents'
                            '?device=%s&component=%s">%s</a>' % (
                                device, value, _shortvalue))
            elif field == 'summary':
                value = urllib.quote(
                    value.replace('<','&lt;').replace('>','&gt;'))
            elif field == 'prodState':
                value = self.context.dmd.convertProdState(value)
            else:
                value = _shortvalue
            data.append(value)
        data.append(zevent.evid)
        data.append(zevent.getCssClass())
        return data


class EventConsoleFields(BrowserView):
    """
    Get the fields for the event console. This is a separate call so that the
    header DOM elements can be created first.

    FIXME: Make the event console a single call.
    """
    def __call__(self):
        return self._getFields()

    @json
    def _getFields(self):
        """
        @return: A list of tuples representing fields and their relative
        lengths
        @rtype: [('field1', 10), ('field2', 4), ...]
        """
        context = self.context
        zem = self._getEventManager()
        if hasattr(context, 'getResultFields'):
            fields = context.getResultFields()
        else:
            if hasattr(context, 'event_key'): base = context
            else: base = zem.dmd.Events
            fields = zem.lookupManagedEntityResultFields(base.event_key)
        lens = map(zem.getAvgFieldLength, fields)
        total = sum(lens)
        lens = map(lambda x:x/total*100, lens)
        zipped = zip(fields, lens)
        return zipped

    def _getEventManager(self):
        return self.context.dmd.ZenEventManager


class HistoryConsole(EventConsole):
    """
    Same as the event console, only it accesses the history table.
    """
    def _getEventManager(self):
        return self.context.dmd.ZenEventHistory


class HistoryConsoleFields(EventConsoleFields):
    """
    Same as the event console fields, only for history.

    FIXME: Is this used anywhere?
    """
    def _getEventManager(self):
        return self.context.dmd.ZenEventHistory


