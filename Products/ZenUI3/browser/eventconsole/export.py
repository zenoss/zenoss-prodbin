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
        events = self._query(**state['params'])
        # Send the events to the appropriate formatting method
        result = getattr(self, type)(state['params']['fields'], events)
        return result

    def _query(self, fields, sort, dir, params=None):
        evutil = IEventManagerProxy(self)
        zem = evutil.event_manager()
        if isinstance(params, basestring): params = unjson(params)
        if not params:
            params = {}
        args = dict(
            resultFields=fields,
            orderby="%s %s" % (sort, dir),
            filters=params
        )
        data = zem.getEventListME(self.context, **args)
        data = [evutil.extract_data_from_zevent(ev, fields) for ev in data]
        return data

    def csv(self, fieldsAndLabels, objects, out=None):
        import csv
        import StringIO
        if out:
            buffer = out
        else:
            buffer = StringIO.StringIO()
        fields = []
        labels = []
        if not fieldsAndLabels:
            fieldsAndLabels = []
        if not objects:
            objects = []
        for p in fieldsAndLabels:
            if isinstance(p, tuple):
                fields.append(p[0])
                labels.append(p[1])
            else:
                fields.append(p)
                labels.append(p)
        writer = csv.writer(buffer)
        writer.writerow(labels)
        def getDataField(thing, field):
            if isinstance(thing, dict):
                value = thing.get(field, '')
            elif isinstance(thing, list) or isinstance(thing, tuple):
                value = thing[int(field)]
            else:
                value = getattr(thing, field, '')
            if isinstance(value, ZenModelBase):
                value = value.id
            elif callable(value):
                value = value()
            if value == None:
                value = ''
            return str(value)
        for o in objects:
            writer.writerow([getDataField(o,f) for f in fields])
        if out:
            result = None
        else:
            result = buffer.getvalue()

        # Set the headers appropriately
        self.request.response.setHeader('Content-Type',
                                        'application/vns.ms-excel')
        self.request.response.setHeader('Content-Disposition',
                                        'attachment; filename=events.csv')
        return result

    def xml(self, parameters):
        pass
