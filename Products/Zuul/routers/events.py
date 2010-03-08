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
import time

from Products.ZenUI3.browser.eventconsole.grid import column_config
from Products.ZenUtils.Ext import DirectRouter
from Products.ZenUtils.extdirect.router import DirectResponse
from Products.Zuul import getFacade
from Products.Zuul.decorators import require
from _mysql_exceptions import OperationalError

class EventsRouter(DirectRouter):

    def __init__(self, context, request):
        super(EventsRouter, self).__init__(context, request)
        self.api = getFacade('event', context)

    @require('View')
    def query(self, limit=None, start=None, sort=None, dir=None, params=None,
              history=False, uid=None, criteria=()):
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
            message = e.__class__.__name__ + ' ' + str(e)
            return DirectResponse.fail(message)
        
    @require('View History')
    def queryHistory(self, limit, start, sort, dir, params):
        return self.query(limit, start, sort, dir, params, history=True)

    @require('Manage Events')
    def acknowledge(self, evids=None, excludeIds=None, selectState=None,
                    field=None, direction=None, params=None, history=False,
                    uid=None, asof=None):
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
        if uid is None:
            uid = self.context
        self.api.unacknowledge(evids, excludeIds, selectState, field, direction,
                               params, asof=asof, context=uid, history=history)
        return DirectResponse.succeed()

    @require('Manage Events')
    def reopen(self, evids=None, excludeIds=None, selectState=None, field=None, 
               direction=None, params=None, history=False, uid=None, asof=None):
        if uid is None:
            uid = self.context
        self.api.reopen(evids, excludeIds, selectState, field, direction, 
                        params, asof=asof, context=uid, history=history)
        return DirectResponse.succeed()

    @require('Manage Events')
    def close(self, evids=None, excludeIds=None, selectState=None, field=None, 
              direction=None, params=None, history=False, uid=None, asof=None):
        if uid is None:
            uid = self.context
        self.api.close(evids, excludeIds, selectState, field, direction, params,
                        asof=asof, context=uid, history=history)
        return DirectResponse.succeed()

    @require('View')
    def detail(self, evid, history=False):
        event = self.api.detail(evid, history)
        if event:
            return DirectResponse.succeed( event=[event])

    @require('Manage Events')
    def write_log(self, evid=None, message=None, history=False):
        self.api.log(evid, message, history)

    @require('Manage Events')
    def classify(self, evids, evclass, history=False):
        zem = self.api._event_manager(history)
        msg, url = zem.manage_createEventMap(evclass, evids)
        if url:
            msg += "<br/><br/><a href='%s'>Go to the new mapping.</a>" % url
        return DirectResponse(msg, success=bool(url))

    @require('Manage Events')
    def add_event(self, summary, device, component, severity, evclasskey, evclass):
        evid = self.api.create(summary, severity, device, component,
                               eventClassKey=evclasskey, eventClass=evclass)
        return DirectResponse.succeed(evid=evid)

    def column_config(self, uid=None):
        if uid==None:
            uid = self.context
        return column_config(self.api.fields(uid), self.request)

