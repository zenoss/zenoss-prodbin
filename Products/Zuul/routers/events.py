import time

from zope.component import queryUtility

from Products.ZenUI3.browser.eventconsole.grid import column_config
from Products.ZenUtils.Ext import DirectRouter
from Products.ZenUtils.json import unjson
from Products.Zuul.interfaces import IEventFacade


class EventsRouter(DirectRouter):

    def __init__(self, context, request):
        super(EventsRouter, self).__init__(context, request)
        self.api = queryUtility(IEventFacade)

    def query(self, limit, start, sort, dir, params):
        events = self.api.query(limit, start, sort, dir, params)
        self._set_asof(time.time())
        return {'events':events['data']}

    def acknowledge(self, evids=None, ranges=None, start=None, limit=None,
                    field=None, direction=None, params=None):
        self.api.acknowledge(evids, ranges, start, limit, field, direction,
                             params, asof=self._asof)
        return {'success':True}

    def unacknowledge(self, evids=None, ranges=None, start=None, limit=None,
                      field=None, direction=None, params=None):
        self.api.unacknowledge(evids, ranges, start, limit, field, direction,
                               params, asof=self._asof)
        return {'success':True}

    def reopen(self, evids=None, ranges=None, start=None, limit=None,
                      field=None, direction=None, params=None):
        self.api.reopen(evids, ranges, start, limit, field, direction, params,
                        asof=self._asof)
        return {'success':True}

    def close(self, evids=None, ranges=None, start=None, limit=None,
              field=None, direction=None, params=None):
        self.api.close(evids, ranges, start, limit, field, direction, params,
                        asof=self._asof)
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

        @param state: The state for which ranges should be calculated.
        @type state: int
        @param sort: The column by which the events should be sorted.
        @type sort: str
        @param dir: The direction in which events should be sorted, either
                    "ASC" or "DESC"
        @type dir: str
        @param filters: Values for which to create filters (e.g.,
                        {'device':'^loc.*$', 'severity':[4, 5]})
        @type filters: dict or JSON str representing dict
        @return: A list of lists comprising indices marking the boundaries of
                 contiguous events with the given state.
        @rtype: list
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
        zem = self.api._event_manager()
        where = zem.lookupManagedEntityWhere(self.context)
        where = zem.filteredWhere(where, params)
        if self._asof:
            where += " and not (stateChange>%s and eventState=0)" % (
                                                self.dateDB(self._asof))
        table = self.api._is_history() and 'history' or 'status'
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
        event = self.api.detail(evid, history)
        if event:
            return { 'event': [event] }

    def write_log(self, evid=None, message=None, history=False):
        self.api.log(evid, message, history)

    def classify(self, evids, evclass):
        zem = self.api._event_manager()
        msg, url = zem.manage_createEventMap(evclass, evids)
        if url:
            msg += "<br/><br/><a href='%s'>Go to the new mapping.</a>" % url
        return {'success':bool(url), 'msg': msg}

    def add_event(self, summary, device, component, severity, evclasskey, evclass):
        evid = self.api.create(summary, severity, device, component,
                               eventClassKey=evclasskey, eventClass=evclass)
        return {'success':True, 'evid':evid}

    def column_config(self):
        return column_config(self.api.fields(self.context), self.request)

