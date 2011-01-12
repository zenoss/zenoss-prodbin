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


    def _query(self, history, fields, sort, dir, params=None):
        jsonParams = params
        if isinstance(params, dict):
            jsonParams = json.dumps(params)
        limit = 1000
        zepRouter = EventsRouter(self.context, self.request)
        archive = history
        summaryEvents = zepRouter.query(archive=archive, limit=limit, sort=sort, 
                                    dir=dir, params=jsonParams, detailFormat=True)
        data = summaryEvents.data.get('events', [])
        eventData = []
        field_names = set()
        for event in data:
            eventDict = {}
            # default values for fields some optional fields in ZEP events
            eventDict['DeviceClass']= "NOT IMPLEMENTED"
            eventDict['ipAddress']= ''

            eventDict.update(event)
            del eventDict['properties']
            for prop in event['properties']:
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

        offset = getTZOffset()
        def timeToUTC(timesstring):
            # Note: canonicalized in MySQL
            timesstring = timesstring[:-4].replace('/', '-').replace(' ', 'T')
            return timesstring + offset

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

        default_field_names = set(zem.getFieldList())
        remaining_field_names = default_field_names - set(['evid', 'dedupid', 'summary',
                          'count', 'firstTime', 'device', 'ipAddress', 'DeviceClass',
                          'lastTime', 'message',
                          ])
        for evt in events:
            xml_output.write('<ZenossEvent ReportTime="%s" >\n' % timeToUTC(evt['firstTime']))
            xml_output.write("""\t<SourceComponent>
\t\t<DeviceClass>%s</DeviceClass>
\t\t<device>%s</device>
\t\t<ipAddress>%s</ipAddress>
\t</SourceComponent>
""" % (evt['DeviceClass'], evt['device'], evt['ipAddress']))
            xml_output.write(reporterComponent)
            xml_output.write('\t<EventId>%s</EventId>\n' % evt['evid'])
            xml_output.write('\t<firstTime>%s</firstTime>\n' % timeToUTC(evt['firstTime']))
            xml_output.write('\t<lastTime>%s</lastTime>\n' % timeToUTC(evt['lastTime']))
            xml_output.write('\t<count>%s</count>\n' % evt['count'])
            xml_output.write('\t<dedupid><![CDATA[%s]]></dedupid>\n' % evt['dedupid'])
            xml_output.write('\t<summary><![CDATA[%s]]></summary>\n' % evt['summary'])
            xml_output.write('\t<message><![CDATA[%s]]></message>\n' % evt['message'])

            for field in remaining_field_names:
                if evt.get(field,'') != '':
                    xml_output.write('\t<%s>%s</%s>\n' % (field, evt.get(field), field))

            extraFields = [field for field in sorted(evt.keys())
                           if field not in default_field_names]

            if extraFields:
                xml_output.write('\t<EventSpecific>\n')
                for field in extraFields:
                    value = evt[field]
                    xml_output.write("\t\t<property name='%s'><![CDATA[%s]]></property>\n" % (
                                 str(field), str(value)))
                xml_output.write('\t</EventSpecific>\n')

            xml_output.write('</ZenossEvent>\n')

        xml_output.write( "</ZenossEvents>\n" )

        return 'text/xml', 'events.xml', xml_output.getvalue()

