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
"""
Operations for Events.

Available at:  /zport/dmd/evconsole_router
"""

import time
import logging
log = logging.getLogger('zen.event_router')

from Products.ZenUI3.browser.eventconsole.grid import column_config
from Products.ZenUtils.Ext import DirectRouter
from Products.ZenUtils.extdirect.router import DirectResponse
from Products.Zuul import getFacade, marshal
from Products.Zuul.decorators import require
from _mysql_exceptions import OperationalError

class EventsRouter(DirectRouter):
    """
    A JSON/ExtDirect interface to operations on events
    """

    def __init__(self, context, request):
        super(EventsRouter, self).__init__(context, request)
        self.api = getFacade('event', context)

    @require('ZenCommon')
    def query(self, limit=0, start=0, sort='lastTime', dir='DESC', params=None,
              history=False, uid=None, criteria=()):
        """
        Query for events.

        @type  limit: integer
        @param limit: (optional) Max index of events to retrieve (default: 0)
        @type  start: integer
        @param start: (optional) Min index of events to retrieve (default: 0)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return results (default:
                     'lastTime')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'DESC')
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       (default: None)
        @type  history: boolean
        @param history: (optional) True to search the event history table instead
                        of active events (default: False)
        @type  uid: string
        @param uid: (optional) Context for the query (default: None)
        @type  criteria: [dictionary]
        @param criteria: (optional) A list of key-value pairs to to build query's
                         where clause (default: None)
        @rtype:   dictionary
        @return:  B{Properties}:
           - events: ([dictionary]) List of objects representing events
           - totalCount: (integer) Total count of events returned
           - asof: (float) Current time
        """
        try:
            if uid is None:
                uid = self.context
            events = self.api.query(limit, start, sort, dir, params, uid, criteria,
                                   history)
            return {'events':events['data'],
                    'totalCount': events['total'],
                    'asof': time.time() }
        except OperationalError, oe:
            message = str(oe)
            return DirectResponse.fail(message)
        except Exception, e:
            log.exception('Query is failing')
            message = e.__class__.__name__ + ' ' + str(e)
            return DirectResponse.fail(message)

    @require('ZenCommon')
    def queryHistory(self, limit, start, sort, dir, params):
        """
        Query history table for events.

        @type  limit: integer
        @param limit: (optional) Max index of events to retrieve (default: 0)
        @type  start: integer
        @param start: (optional) Min index of events to retrieve (default: 0)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return results (default:
                     'lastTime')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'DESC')
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       (default: None)
        @rtype:   dictionary
        @return:  B{Properties}:
           - events: ([dictionary]) List of objects representing events
           - totalCount: (integer) Total count of events returned
           - asof: (float) Current time
        """
        return self.query(limit, start, sort, dir, params, history=True)

    @require('Manage Events')
    def acknowledge(self, evids=None, excludeIds=None, selectState=None,
                    field=None, direction=None, params=None, history=False,
                    uid=None, asof=None):
        """
        Acknowledge event(s).

        @type  evids: [string]
        @param evids: (optional) List of event IDs to acknowledge (default: None)
        @type  excludeIds: [string]
        @param excludeIds: (optional) List of event IDs to exclude from
                           acknowledgment (default: None)
        @type  selectState: string
        @param selectState: (optional) Select event ids based on select state.
                            Available values are: All, New, Acknowledged, and
                            Suppressed (default: None)
        @type  field: string
        @param field: (optional) Field key to filter gathered events (default:
                      None)
        @type  direction: string
        @param direction: (optional) Sort order; can be either 'ASC' or 'DESC'
                          (default: 'DESC')
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       (default: None)
        @type  history: boolean
        @param history: (optional) True to use the event history table instead
                        of active events (default: False)
        @type  uid: string
        @param uid: (optional) Context for the query (default: None)
        @type  asof: float
        @param asof: (optional) Only acknowledge if there has been no state
                     change since this time (default: None)
        @rtype:   DirectResponse
        @return:  Success message
        """
        if uid is None:
            uid = self.context
        self.api.acknowledge(evids, excludeIds, selectState, field, direction,
                             params, asof=asof, context=uid,
                             history=history)
        return DirectResponse.succeed()

    @require('Manage Events')
    def unacknowledge(self, evids=None, excludeIds=None, selectState=None,
                      field=None, direction=None, params=None, history=False,
                      uid=None, asof=None):
        """
        Unacknowledge event(s).

        @type  evids: [string]
        @param evids: (optional) List of event IDs to unacknowledge (default: None)
        @type  excludeIds: [string]
        @param excludeIds: (optional) List of event IDs to exclude from
                           unacknowledgment (default: None)
        @type  selectState: string
        @param selectState: (optional) Select event ids based on select state.
                            Available values are: All, New, Acknowledged, and
                            Suppressed (default: None)
        @type  field: string
        @param field: (optional) Field key to filter gathered events (default:
                      None)
        @type  direction: string
        @param direction: (optional) Sort order; can be either 'ASC' or 'DESC'
                          (default: 'DESC')
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       (default: None)
        @type  history: boolean
        @param history: (optional) True to use the event history table instead
                        of active events (default: False)
        @type  uid: string
        @param uid: (optional) Context for the query (default: None)
        @type  asof: float
        @param asof: (optional) Only unacknowledge if there has been no state
                     change since this time (default: None)
        @rtype:   DirectResponse
        @return:  Success message
        """
        if uid is None:
            uid = self.context
        self.api.unacknowledge(evids, excludeIds, selectState, field, direction,
                               params, asof=asof, context=uid, history=history)
        return DirectResponse.succeed()

    @require('Manage Events')
    def reopen(self, evids=None, excludeIds=None, selectState=None, field=None,
               direction=None, params=None, history=False, uid=None, asof=None):
        """
        Reopen event(s).

        @type  evids: [string]
        @param evids: (optional) List of event IDs to reopen (default: None)
        @type  excludeIds: [string]
        @param excludeIds: (optional) List of event IDs to exclude from
                           reopen (default: None)
        @type  selectState: string
        @param selectState: (optional) Select event ids based on select state.
                            Available values are: All, New, Acknowledged, and
                            Suppressed (default: None)
        @type  field: string
        @param field: (optional) Field key to filter gathered events (default:
                      None)
        @type  direction: string
        @param direction: (optional) Sort order; can be either 'ASC' or 'DESC'
                          (default: 'DESC')
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       (default: None)
        @type  history: boolean
        @param history: (optional) True to use the event history table instead
                        of active events (default: False)
        @type  uid: string
        @param uid: (optional) Context for the query (default: None)
        @type  asof: float
        @param asof: (optional) Only reopen if there has been no state
                     change since this time (default: None)
        @rtype:   DirectResponse
        @return:  Success message
        """
        if uid is None:
            uid = self.context
        self.api.reopen(evids, excludeIds, selectState, field, direction,
                        params, asof=asof, context=uid, history=history)
        return DirectResponse.succeed()

    @require('Manage Events')
    def close(self, evids=None, excludeIds=None, selectState=None, field=None,
              direction=None, params=None, history=False, uid=None, asof=None):
        """
        Close event(s).

        @type  evids: [string]
        @param evids: (optional) List of event IDs to close (default: None)
        @type  excludeIds: [string]
        @param excludeIds: (optional) List of event IDs to exclude from
                           close (default: None)
        @type  selectState: string
        @param selectState: (optional) Select event ids based on select state.
                            Available values are: All, New, Acknowledged, and
                            Suppressed (default: None)
        @type  field: string
        @param field: (optional) Field key to filter gathered events (default:
                      None)
        @type  direction: string
        @param direction: (optional) Sort order; can be either 'ASC' or 'DESC'
                          (default: 'DESC')
        @type  params: dictionary
        @param params: (optional) Key-value pair of filters for this search.
                       (default: None)
        @type  history: boolean
        @param history: (optional) True to use the event history table instead
                        of active events (default: False)
        @type  uid: string
        @param uid: (optional) Context for the query (default: None)
        @type  asof: float
        @param asof: (optional) Only close if there has been no state
                     change since this time (default: None)
        @rtype:   DirectResponse
        @return:  Success message
        """
        if uid is None:
            uid = self.context
        self.api.close(evids, excludeIds, selectState, field, direction, params,
                        asof=asof, context=uid, history=history)
        return DirectResponse.succeed()

    @require('ZenCommon')
    def detail(self, evid, history=False):
        """
        Get event details.

        @type  evid: string
        @param evid: Event ID to get details
        @type  history: boolean
        @param history: (optional) True to search the event history table instead
                        of active events (default: False)
        @rtype:   DirectResponse
        @return:  B{Properties}:
           - event: ([dictionary]) List containing a dictionary representing
                    event details
        """
        event = self.api.detail(evid, history)
        if event:
            return DirectResponse.succeed(event=[event])

    @require('Manage Events')
    def write_log(self, evid=None, message=None, history=False):
        """
        Write a message to an event's log.

        @type  evid: string
        @param evid: Event ID to log to
        @type  message: string
        @param message: Message to log
        @type  history: boolean
        @param history: (optional) True to use the event history table instead
                        of active events (default: False)
        @rtype:   DirectResponse
        @return:  Success message
        """
        self.api.log(evid, message, history)
        return DirectResponse.succeed()

    @require('Manage Events')
    def classify(self, evids, evclass, history=False):
        """
        Associate event(s) with an event class.

        @type  evids: [string]
        @param evids: List of event ID's to classify
        @type  evclass: string
        @param evclass: Event class to associate events to
        @type  history: boolean
        @param history: (optional) True to use the event history table instead
                        of active events (default: False)
        @rtype:   DirectResponse
        @return:  B{Properties}:
           - msg: (string) Success/failure message
           - success: (boolean) True if class update successful
        """
        zem = self.api._event_manager(history)
        msg, url = zem.manage_createEventMap(evclass, evids)
        if url:
            msg += "<br/><br/><a href='%s'>Go to the new mapping.</a>" % url
        return DirectResponse(msg, success=bool(url))

    @require('Manage Events')
    def add_event(self, summary, device, component, severity, evclasskey, evclass):
        """
        Create a new event.

        @type  summary: string
        @param summary: New event's summary
        @type  device: string
        @param device: Device uid to use for new event
        @type  component: string
        @param component: Component uid to use for new event
        @type  severity: string
        @param severity: Severity of new event. Can be one of the following:
                         Critical, Error, Warning, Info, Debug, or Clear
        @type  evclasskey: string
        @param evclasskey: The Event Class Key to assign to this event
        @type  evclass: string
        @param evclass: Event class for the new event
        @rtype:   DirectResponse
        @return:  B{Properties}:
           - evid: (string) The id of the created event
        """
        evid = self.api.create(summary, severity, device, component,
                               eventClassKey=evclasskey, eventClass=evclass)
        return DirectResponse.succeed(evid=evid)

    def column_config(self, uid=None, history=False):
        """
        Get the current event console field column configuration.

        @type  uid: string
        @param uid: (optional) UID context to use (default: None)
        @type  history: boolean
        @param history: (optional) True to use the event history table instead
                        of active events (default: False)
        @rtype:   [dictionary]
        @return:  A list of objects representing field columns
        """
        return column_config(self.request, history)

