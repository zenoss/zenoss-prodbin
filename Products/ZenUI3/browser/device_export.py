##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
from Products import Zuul
from Products.Five.browser import BrowserView
from Products.ZenUtils.jsonutils import unjson
from Products.Zuul.facades.devicefacade import DeviceFacade
from xml.etree.ElementTree import Element, tostring

log = logging.getLogger('zen.deviceexporter')


class DeviceExporter(BrowserView):

    def __call__(self):
        body = unjson(self.request.form['body'])
        type = body.get('type')
        getattr(self, type)(self.request.response, self._query(body), body['fields'])

    def _query(self, params):
        device_router = DeviceFacade(self.context)
        devices = device_router.getDevices(uid=params['uid'],
                                           sort=params['sort'],
                                           dir=params['sdir'],
                                           params=params['params'],
                                           limit=None)
        return Zuul.marshal(devices.results, params['fields'])

    @staticmethod
    def _xml_event(value):
        for event_kind, event_fields in value.iteritems():
            event_kind_field = Element(event_kind)
            for event_field_key, event_field_value in event_fields.iteritems():
                event_field = Element(event_field_key)
                event_field.text = str(event_field_value)
                event_kind_field.append(event_field)
            yield event_kind_field

    def xml(self, response, devices, fields):
        response.setHeader('Content-Type', 'text/xml; charset=utf-8')
        response.setHeader('Content-Disposition', 'attachment; filename=devices.xml')
        response.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        response.write('<ZenosDevices>\n')
        for device in devices:
            xml_device = Element('ZenossDevice')
            for field in fields:
                device_field = Element(field)
                value = device.get(field, '')
                if field == 'events':
                    for event in self._xml_event(value):
                        device_field.append(event)
                elif field in ['systems', 'groups']:
                    for s in value:
                        sub_field = Element(field[:-1])
                        sub_field.text = str(s.get('name'))
                        device_field.append(sub_field)
                elif isinstance(value, dict):
                    value = value.get('name', '')
                    device_field.text = str(value)
                else:
                    device_field.text = str(value)
                xml_device.append(device_field)
            response.write(tostring(xml_device))
        response.write("")
        response.write('<ZenosDevices>\n')

    @staticmethod
    def csv(response, devices, fields):
        response.setHeader('Content-Type', 'application/vns.ms-excel')
        response.setHeader('Content-Disposition', 'attachment; filename=devices.csv')
        from csv import writer
        writer = writer(response)
        wrote_header = False
        fields_to_write = [f for f in fields if f != 'events']
        for device in devices:
            data = []
            for field in fields:
                value = device.get(field, '')
                if isinstance(value, list):
                    value = "|".join([v.get('name') for v in value])
                if isinstance(value, dict):
                    if field == 'events':
                        for event_type in value.keys():
                            fields_to_write.append("%s_events_count" % event_type)
                            fields_to_write.append("%s_events_acknowledged" % event_type)
                            data.append(str(value.get(event_type).get('count')))
                            data.append(str(value.get(event_type).get('acknowledged_count')))
                    else:
                        value = value.get('name', None)
                if not field == 'events':
                    data.append(str(value).strip() if value or value is 0 else '')
            if not wrote_header:
                writer.writerow(fields_to_write)
                wrote_header = True
            writer.writerow(data)

