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

__doc__ = """export

Given a list of events to export, format them
appropriately and then return back a string
"""

import StringIO

from Products.Five.browser import BrowserView

from Products.ZenModel.ZenModelBase import ZenModelBase
from Products.ZenUtils.json import unjson

from interfaces import IEventManagerProxy

class EventsExporter(BrowserView):
    def __call__(self):
        body = self.request.form['body']
        state = unjson(body)
        type = state['type']

        # Get the events according to grid state
        fields, events = self._query(**state['params'])

        # Send the events to the appropriate formatting method
        ctype, filename, result = getattr(self, type)(fields, events)

        # Set the headers appropriately
        self.request.response.setHeader('Content-Type', ctype)
        self.request.response.setHeader('Content-Disposition',
                                        'attachment; filename=' + filename)
        return result


    def _query(self, fields, sort, dir, params=None):
        evutil = IEventManagerProxy(self)
        zem = evutil.event_manager()
        if isinstance(params, basestring):
            params = unjson(params)
        if not params:
            params = {}
        args = dict(
            resultFields=['evid'],
            orderby="%s %s" % (sort, dir),
            filters=params
        )
        all_events = zem.getEventListME(self.context, **args)
        # First item is the list of default fields
        field_names = set(zem.getFieldList())
        events = []
        for evt in all_events:
            evobj = zem.getEventDetailFromStatusOrHistory(evid=evt.evid)
            evt_dict = dict(evobj.getEventFields())
            evt_dict.update(dict(evobj.getEventDetails()))
            field_names.update(evt_dict.keys())
            events.append(evt_dict)
            
        return list(field_names), events


    def csv(self, fields, events):
        import csv
        buffer = StringIO.StringIO()
        writer = csv.writer(buffer)

        writer.writerow(fields)

        for evt in events:
            data = [str(evt.get(field, '')).replace('\n', ' ').strip() for field in fields]
            writer.writerow(data)

        return 'application/vns.ms-excel', 'events.csv', buffer.getvalue()


    def xml(self, fields, events):
        xml_output = StringIO.StringIO()

        xml_output.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        xml_output.write( "<events>\n" )

        for evt in events:
            xml_output.write('<event ')
            for field, value in sorted(evt.items()):
                name = str(field).replace('.', '__DOT__').replace(' ', '__SPACE__')
                if name[0].isdigit():
                    name = 'EVENT_PREFIX__' + name
                xml_output.write('%s="%s" ' % (name, str(value)))
            xml_output.write(' />\n')

        xml_output.write( "</events>\n" )

        return 'text/xml', 'events.xml', xml_output.getvalue()

