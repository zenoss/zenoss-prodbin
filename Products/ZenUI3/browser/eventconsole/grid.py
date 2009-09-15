from zope.interface import implements
import copy

from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from Products.ZenUtils.Ext import DirectRouter, DirectProviderDefinition
from Products.ZenUI3.utils.json import json, unjson
from Products.ZenUI3.utils.javascript import JavaScriptSnippet
from Products.ZenUI3.utils.javascript import JavaScriptSnippetManager

from Products.ZenUI3.browser.eventconsole.columns import COLUMN_CONFIG

from interfaces import IEventManagerProxy


class EventConsoleView(BrowserView):
    __call__ = ViewPageTemplateFile('console.pt')
    # Need an id so the tabs can tell what's going on
    __call__.id = 'viewEvents'


class HistoryConsoleView(BrowserView):
    __call__ = ViewPageTemplateFile('historyconsole.pt')
    # Need an id so the tabs can tell what's going on
    __call__.id = 'viewHistoryEvents'


class EventConsole(DirectRouter):

    def _evmgr(self, forceHistory=False):
        return IEventManagerProxy(self).event_manager(forceHistory)

    # BEGIN PUBLIC METHODS

    def query(self, limit, start, sort, dir, evid=None, params=None):
        """
        Data that populates the event console.
        """
        context = self.context
        if isinstance(params, basestring): params = unjson(params)
        zem = self._evmgr()
        start = max(start, 0)

        if hasattr(context, 'getResultFields'):
          fields = context.getResultFields()
        else:
          # Use default result fields
          if hasattr(context, 'event_key'):
              base = context
          else:
              base = zem.dmd.Events
          fields = zem.lookupManagedEntityResultFields(base.event_key)

        if not params:
            params = {}

        args = dict(
            offset=start,
            rows=limit,
            resultFields=fields,
            getTotalCount=True,
            sort=sort,
            orderby="%s %s, lastTime DESC" % (sort, dir),
            filters=params
        )
        if evid: args['evid'] = evid

        data, totalCount = zem.getEventListME(context, **args)
        data_extractor = IEventManagerProxy(self).extract_data_from_zevent
        results = [data_extractor(ev, fields) for ev in data]

        return {
            'events': results,
            'totalCount': totalCount
        }

    def acknowledge(self, evids=None, ranges=None, start=None, limit=None,
                    field=None, direction=None, params=None):
        zem = self._evmgr()
        range_evids = zem.getEventIDsFromRanges(self.context, field, direction,
                                                start, limit, params, evids,
                                                ranges)
        zem.manage_ackEvents(range_evids)
        return {'success':True}

    def close(self, evids=None, ranges=None, start=None, limit=None,
              field=None, direction=None, params=None):
        zem = self._evmgr()
        range_evids = zem.getEventIDsFromRanges(self.context, field, direction,
                                                start, limit, params, evids,
                                                ranges)
        zem.manage_deleteEvents(range_evids)
        return {'success':True}

    def state_ranges(self, state=1, field='severity', direction='DESC',
                     params=None):
        """
        Get a list of ranges describing contiguous blocks of events with a
        certain state.

        For example, in this one-column table:

            A
            A
            A
            B
            B
            A
            B
            B
            B

        The 'A' ranges are [[1,3], [6,6]], and the 'B' ranges are
        [[4,5],[7,9]].

        This is achieved by keeping a running total number of rows (@row in
        query_tpl below), and marking those rows where the eventState switches
        from one to another (@idx in query_tpl below). Selecting that from a
        subquery that selects the actual events (given filters and sort) yields
        the row number and event state of the first row of each contiguous
        block of events:

            ((1L, 0), (345L, 1), (347L, 0))

        One can then determine the ranges (in the above example, the new (0)
        events are at indices [[1,344],[347,END]] where END is the total number
        of rows).

        Calculating the total number of rows returned by the innermost subquery
        might be costly, so we return a single-member range and let the browser
        fill in the total, which it already knows, as the subquery necessarily
        also describes the current state of the grid.
        """
        query_tpl = """
        select row, eventstate from (
            select @row:=if(@row is null, 1, @row+1) as row,
                   @idx:=if(@marker!=eventstate, 1, 0) as idx,
                   @marker:=eventstate as eventstate
            from (%s) as x
        ) as y
        where idx=1;
        """
        if params is None:
            params = {}
        elif isinstance(params, basestring):
            params = unjson(params)
        zem = self._evmgr()
        where = zem.lookupManagedEntityWhere(self.context)
        where = zem.filteredWhere(where, params)
        table = IEventManagerProxy(self).is_history and 'history' or 'status'
        q = 'select eventState from %s where %s ' % (table, where)
        q += 'order by %s %s' % (field, direction)
        query = query_tpl % q
        try:
            conn = zem.connect()
            curs = conn.cursor()
            curs.execute("set @row:=0;")
            curs.execute("set @marker:=999;")
            curs.execute(query)
            result = curs.fetchall()
        finally:
            curs.close()
        ranges = []
        currange = []
        for idx, st in result:
            if st==state:
                currange.append(idx)
            else:
                if len(currange)==1:
                    currange.append(idx-1)
                    ranges.append(currange)
                    currange = []
        if currange:
            ranges.append(currange)
        return ranges

    def detail(self, evid, history=False):
        zem = self._evmgr(history)
        details = zem.getEventDetail(evid)
        fields = dict(details.getEventFields())
        event = fields.copy()
        properties = fields.items() + dict(details._details).items()
        properties = [{'key':key,'value':value} for key, value in properties]
        event['properties'] = properties
        event['log'] = details._logs
        for f in ('device', 'component', 'eventClass'):
            func = getattr(IEventManagerProxy(self), '_get_%s_url' % f)
            if f=='component':
                args = event['device'], event['component']
            else:
                args = [event[f]]
            url = func(*args)
            if url:
                event[f+'_url'] = url
        return { 'event': [event] }

    def write_log(self, evid=None, message=None, history=False):
        zem = self._evmgr(history)
        zem.manage_addLogMessage(evid, message)

    def classify(self, evids, evclass):
        zem = self._evmgr()
        msg, url = zem.manage_createEventMap(evclass, evids)
        if url:
            msg += "<br/><br/><a href='%s'>Go to the new mapping.</a>" % url
        return {'success':bool(url), 'msg': msg}

    def add_event(self, summary, device, component, severity, evclasskey,
                  evclass):
        zem = self._evmgr()
        if isinstance(severity, basestring):
            sevs = ['Clear', 'Debug', 'Info', 'Warning', 'Error', 'Critical']
            severity = sevs.index(severity)
        evid = zem.manage_addEvent(dict(
            device=device,
            summary=summary,
            component=component,
            severity=severity,
            eventClassKey=evclasskey,
            eventClass=evclass
        ))
        return {'success':True, 'evid':evid}

    def column_config(self):
        f = getattr(self.context, 'getResultFields', None)
        if f is None:
            fields = self._evmgr().getEventResultFields(self.context)
        else:
            fields = f()
        return column_config(fields)


class EventConsoleAPIDefinition(DirectProviderDefinition):
    _router = EventConsole
    _url = 'evconsole_router'


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


def column_config(fields):
    defs = []
    for field in fields:
        col = COLUMN_CONFIG[field].copy()
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


class GridColumnDefinitions(JavaScriptSnippet):

    def snippet(self):
        zem = IEventManagerProxy(self).event_manager()
        result = ["Ext.onReady(function(){Zenoss.env.COLUMN_DEFINITIONS=["]
        f = getattr(self.context, 'getResultFields', None)
        if f is None:
            fields = zem.getEventResultFields(self.context)
        else:
            fields = f()
        defs = column_config(fields)
        result.append(',\n'.join(defs))
        result.append(']});')
        result = '\n'.join(result)
        return result

