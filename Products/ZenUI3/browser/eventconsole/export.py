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

DETAILS_KEY = "details"


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

    def _get_event_fields(self, event, requested_fields):
        """
            Returns the fields present in the event placing
            requested_events first, details last and rest of
            the fiels in alphabetic order
        """
        returned_fields = set(event.keys())
        header = []
        # Lets put the requested fields first
        if requested_fields:
            for field in requested_fields:
                if field in returned_fields:
                    returned_fields.remove(field)
                header.append(field)
        # returned_fields has the fields that have not been explicitely
        #  requested. lets append them ensuring details are at the end
        show_details = False
        if DETAILS_KEY in returned_fields:
            returned_fields.remove(DETAILS_KEY)
            show_details = True
        not_requested_fields = list(sorted(returned_fields,
                                           key=lambda(x): x.lower()
                                           ))
        if show_details:
            not_requested_fields.append(DETAILS_KEY)
        header.extend(not_requested_fields)

        return header

    def _query(self, archive, uid=None, fields=None, sort=None, dir=None,
               evids=None, excludeIds=None, params=None):
        jsonParams = params
        if isinstance(jsonParams, dict):
            jsonParams = json.dumps(jsonParams)
        zepRouter = EventsRouter(self.context, self.request)
        summaryEvents = zepRouter.queryGenerator(archive=archive, sort=sort,
                                                 dir=dir, evids=evids,
                                                 excludeIds=excludeIds,
                                                 params=jsonParams, uid=uid,
                                                 detailFormat=True)
        header = []
        for event in summaryEvents:
            # default values for fields some optional fields in ZEP events
            if isinstance(event.get('DeviceClass'), dict):
                event['DeviceClass'] = event['DeviceClass']['name']
            if 'device_uuid' in event:
                del event['device_uuid']

            parsed_details = {detail['key']: detail['value']
                              for detail in event[DETAILS_KEY]
                              if detail['key'] not in event
                              }
            event[DETAILS_KEY] = parsed_details

            del event['log']
            if not header:
                header = self._get_event_fields(event, fields)

            yield header, event

    def csv(self, response, archive, **params):
        response.setHeader('Content-Type', 'application/vns.ms-excel')
        response.setHeader('Content-Disposition',
                           'attachment; filename=events.csv')
        from csv import writer
        writer = writer(response)

        wroteHeader = False
        for fields, evt in self._query(archive, **params):
            data = []
            if not wroteHeader:
                writer.writerow(fields)
                wroteHeader = True
            details = evt.get(DETAILS_KEY)

            for field in fields:
                val = evt.get(field, '')
                if field in ("lastTime", "firstTime") and val:
                    val = datetime.utcfromtimestamp(val).isoformat()
                elif field == DETAILS_KEY and val:
                    # ZEN-ZEN-23871: add all details in one column
                    val = json.dumps(val)
                elif not (val or val is 0) and details:
                    # ZEN-27617: fill in value for requested field in details
                    val = details.get(field, '')
                if (val or val is 0):
                    data.append(str(val).replace('\n', ' ').strip())
                else:
                    data.append('')
            writer.writerow(data)

    def xml(self, response, archive, **params):
        response.setHeader('Content-Type', 'text/xml; charset=utf-8')
        response.setHeader('Content-Disposition',
                           'attachment; filename=events.xml')
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
""" % escape(zem.absolute_url_path())

        for fields, evt in self._query(archive, **params):
            firstTime = datetime.utcfromtimestamp(evt['firstTime']).isoformat()
            response.write(
                '<ZenossEvent ReportTime=%s>\n' % quoteattr(firstTime))
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

            details = evt.get(DETAILS_KEY)
            if details:
                evt.update(details)
                del evt[DETAILS_KEY]

            for key, value in evt.iteritems():
                if value is not None:
                    if key in ("lastTime", "firstTime"):
                        value = datetime.utcfromtimestamp(value).isoformat()
                    key = str(key).replace('.', '_')
                    response.write('\t<%s>%s</%s>\n' % (
                                   key, escape(str(value)), key)
                                   )

            response.write('</ZenossEvent>\n')

        response.write("</ZenossEvents>\n")
