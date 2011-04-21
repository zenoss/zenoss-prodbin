###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """export

Given a list of events to export, format them
appropriately and then return back a string
"""

import StringIO
import json

from Products.Five.browser import BrowserView

from Products.ZenModel.ZenModelBase import ZenModelBase
from Products.ZenUtils.jsonutils import unjson
from Products.Zuul.routers.zep import EventsRouter

from interfaces import IEventManagerProxy

class EventsExporter(BrowserView):
    def __call__(self):
        body = self.request.form['body']
        state = unjson(body)
        type = state['type']
        history = state.get('isHistory', False)
        # Get the events according to grid state
        fields, events = self._query(history, **state['params'])

        # Send the events to the appropriate formatting method
        ctype, filename, result = getattr(self, type)(fields, events)

        # Set the headers appropriately
        self.request.response.setHeader('Content-Type', ctype)
        self.request.response.setHeader('Content-Disposition',
                                        'attachment; filename=' + filename)
        return result


    def _query(self, history, fields, sort, dir, uid=None, params=None):
        jsonParams = params
        if isinstance(params, dict):
            jsonParams = json.dumps(params)
        limit = 1000
        zepRouter = EventsRouter(self.context, self.request)
        archive = history
        summaryEvents = zepRouter.query(archive=archive, limit=limit, sort=sort,
                                    dir=dir, params=jsonParams, uid=uid, detailFormat=True)
        data = summaryEvents.data.get('events', [])
        eventData = []
        field_names = set()
        for event in data:
            eventDict = {}
            # default values for fields some optional fields in ZEP events
            eventDict.update(event)
            if eventDict['DeviceClass']:
                eventDict['DeviceClass'] =  eventDict['DeviceClass']['name']
            del eventDict['device_uuid']
            del eventDict['details']
            for prop in event['details']:
                eventDict[prop['key']]=prop['value']
            eventData.append(eventDict)
            map(field_names.add, eventDict.keys())
        return list(field_names), eventData


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
        def getTZOffset():
            from time import timezone, altzone, daylight
            zone = timezone
            if daylight != 0:
                zone = altzone

            eastOrWest = '-' # West of GMT
            if zone < 0:
                eastOrWest = '+'
                zone = abs(zone)

            hours, remainder = divmod(zone, 3600)
            minutes, _ = divmod(hours, 60)
            return '%s%02d%02d' % (eastOrWest, hours, minutes)


        xml_output = StringIO.StringIO()

        xml_output.write("""<?xml version="1.0" encoding="UTF-8"?>
<!-- Common Event Format compliant event structure -->
<ZenossEvents>
""")

        evutil = IEventManagerProxy(self)
        zem = evutil.event_manager()
        reporterComponent = """\t<ReporterComponent>
\t\t<url>%s</url>
\t</ReporterComponent>
""" % zem.absolute_url()


        for evt in events:
            xml_output.write('<ZenossEvent ReportTime="%s" >\n' % evt['firstTime'])
            xml_output.write("""\t<SourceComponent>
\t\t<DeviceClass>%s</DeviceClass>
\t\t<device>%s</device>
\t\t<ipAddress>%s</ipAddress>
\t</SourceComponent>
""" % (evt['DeviceClass'], evt['device'], evt['ipAddress']))
            xml_output.write(reporterComponent)
            xml_output.write('\t<dedupid><![CDATA[%s]]></dedupid>\n' % evt['dedupid'])
            xml_output.write('\t<summary><![CDATA[%s]]></summary>\n' % evt['summary'])
            xml_output.write('\t<message><![CDATA[%s]]></message>\n' % evt['message'])

            for field in evt.keys():
                if evt.get(field,'') != '' and field not in ('dedupid', 'summary', 'message'):
                    xml_output.write('\t<%s>%s</%s>\n' % (field.replace(".", "_"), evt.get(field), field.replace(".", "_")))

            xml_output.write('</ZenossEvent>\n')

        xml_output.write( "</ZenossEvents>\n" )

        return 'text/xml', 'events.xml', xml_output.getvalue()

