##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = """export

Given a list of events to export, format them
appropriately and then return back a string
"""

import json
import logging
from datetime import datetime

from Products.Five.browser import BrowserView

from Products.ZenUtils.jsonutils import unjson
from Products.Zuul.routers.zep import EventsRouter

from interfaces import IEventManagerProxy

log = logging.getLogger('zen.eventexport')

class EventsExporter(BrowserView):
    def __call__(self):
        body = self.request.form['body']
        state = unjson(body)
        params = state['params']
        type = state['type']
        archive = state.get('isHistory', False)

        # Send the events to the appropriate formatting method
        filter_params = state['params']['params']
        del state['params']['params']
        params.update(filter_params)
        getattr(self, type)(self.request.response, archive, **params)
        # aborting the long running export transaction so it is not retried
        import transaction
        transaction.abort()

    def _query(self, archive, uid=None, fields=None, sort=None, dir=None, evids=None, excludeIds=None, params=None):
        jsonParams = params
        if isinstance(jsonParams, dict):
            jsonParams = json.dumps(jsonParams)
        zepRouter = EventsRouter(self.context, self.request)
        summaryEvents = zepRouter.queryGenerator(archive=archive, sort=sort, dir=dir,
                                                 evids=evids, excludeIds=excludeIds,
                                                 params=jsonParams, uid=uid, detailFormat=True)
        field_names = []
        for event in summaryEvents:
            # default values for fields some optional fields in ZEP events
            if isinstance(event.get('DeviceClass'), dict):
                event['DeviceClass'] =  event['DeviceClass']['name']
            if 'device_uuid' in event:
                del event['device_uuid']

            details = {detail['key']:detail['value'] for detail in event['details'] if detail['key'] not in event}
            event.update(details)

            del event['details']
            del event['log']
            if not field_names:
                field_names.extend(event.keys())
            yield field_names, event


    def csv(self, response, archive, **params):
        response.setHeader('Content-Type', 'application/vns.ms-excel')
        response.setHeader('Content-Disposition', 'attachment; filename=events.csv')
        from csv import writer
        writer = writer(response)

        wroteHeader = False
        for fields, evt in self._query(archive, **params):
            if not wroteHeader:
                writer.writerow(fields)
                wroteHeader = True
            data = []
            for field in fields:
                val = evt.get(field, '')
                if field in ("lastTime", "firstTime") and val:
                    val = datetime.utcfromtimestamp(val).isoformat()
                data.append(str(val).replace('\n',' ').strip() if val or val is 0 else '')
            writer.writerow(data)

    def xml(self, response, archive, **params):
        response.setHeader('Content-Type', 'text/xml; charset=utf-8')
        response.setHeader('Content-Disposition', 'attachment; filename=events.xml')

        from xml.sax.saxutils import escape, quoteattr
        response.write("""<?xml version="1.0" encoding="UTF-8"?>
<!-- Common Event Format compliant event structure -->
<ZenossEvents>
""")

        evutil = IEventManagerProxy(self)
        zem = evutil.event_manager()
        reporterComponent = """\t<ReporterComponent>
\t\t<url>%s</url>
\t</ReporterComponent>
""" % escape(zem.absolute_url())


        for fields, evt in self._query(archive, **params):
            firstTime = datetime.utcfromtimestamp(evt['firstTime']).isoformat()
            response.write('<ZenossEvent ReportTime=%s>\n' % quoteattr(firstTime))
            response.write("""\t<SourceComponent>
\t\t<DeviceClass>%s</DeviceClass>
\t\t<device>%s</device>
\t\t<ipAddress>%s</ipAddress>
\t</SourceComponent>
""" % (escape(str(evt.get('DeviceClass',''))), escape(str(evt.get('device',''))), escape(str(evt.get('ipAddress', '')))))
            response.write(reporterComponent)
            response.write('\t<dedupid>%s</dedupid>\n' % escape(str(evt.pop('dedupid', ''))))
            response.write('\t<summary>%s</summary>\n' % escape(str(evt.pop('summary', ''))))
            response.write('\t<message>%s</message>\n' % escape(str(evt.pop('message', ''))))

            for key, value in evt.iteritems():
                if value is not None:
                    if key in ("lastTime", "firstTime"):
                        value = datetime.utcfromtimestamp(value).isoformat()
                    key = str(key).replace('.', '_')
                    response.write('\t<%s>%s</%s>\n' % (key, escape(str(value)), key))

            response.write('</ZenossEvent>\n')

        response.write( "</ZenossEvents>\n" )
