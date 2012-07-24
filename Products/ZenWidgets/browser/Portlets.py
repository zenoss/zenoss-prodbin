##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import re
import json

from Products.Five.browser import BrowserView
from Products.AdvancedQuery import Eq, Or

from Products.ZenUtils.Utils import relative_time
from Products.Zuul import getFacade
from Products.ZenEvents.HeartbeatUtils import getHeartbeatObjects
from zenoss.protocols.services import ServiceException
from zenoss.protocols.services.zep import ZepConnectionError
from Products.ZenUtils.guid.interfaces import IGUIDManager
from Products.ZenUtils.jsonutils import json
from Products.ZenUtils.Utils import nocache, formreq, extractPostContent
from Products.ZenWidgets import messaging
from Products.ZenModel.Device import Device
from Products.ZenModel.ZenossSecurity import *
from Products.ZenEvents.browser.EventPillsAndSummaries import \
                                   getDashboardObjectsEventSummary, \
                                   ObjectsEventSummary,    \
                                   getEventPillME

import logging
log = logging.getLogger('zen.portlets')


def zepConnectionError(retval=None):
    def outer(func):
        def inner(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except ZepConnectionError, e:
                msg = 'Connection refused. Check zeneventserver status on <a href="/zport/About/zenossInfo">Daemons</a>'
                messaging.IMessageSender(self.context).sendToBrowser("ZEP connection error",
                                                        msg,
                                                        priority=messaging.CRITICAL,
                                                        sticky=True)
                log.warn("Could not connect to ZEP")
            return retval
        return inner
    return outer

class TopLevelOrganizerPortletView(ObjectsEventSummary):
    """
    Return JSON event summaries for a root organizer.
    """
    @nocache
    @formreq
    def __call__(self, dataRoot):
        self.dataRoot = dataRoot
        return super(TopLevelOrganizerPortletView, self).__call__()

    def _getObs(self):
        return self.context.dmd.getDmdRoot(self.dataRoot).children()


class ProductionStatePortletView(BrowserView):
    """
    Return a map of device to production state in a format suitable for a
    YUI data table.
    """
    @nocache
    @formreq
    def __call__(self, *args, **kwargs):
        return self.getDevProdStateJSON(*args, **kwargs)

    @json
    def getDevProdStateJSON(self, prodStates=['Maintenance']):
        """
        Return a map of device to production state in a format suitable for a
        YUI data table.

        @return: A JSON representation of a dictionary describing devices
        @rtype: "{
            'columns':['Device', 'Prod State'],
            'data':[
                {'Device':'<a href=/>', 'Prod State':'Production'},
                {'Device':'<a href=/>', 'Prod State':'Maintenance'},
            ]}"
        """
        devroot = self.context.dmd.Devices
        if isinstance(prodStates, basestring):
            prodStates = [prodStates]
        orderby, orderdir = 'id', 'asc'
        catalog = getattr(devroot, devroot.default_catalog)
        queries = []
        for state in prodStates:
            queries.append(Eq('getProdState', state))
        query = Or(*queries)
        objects = catalog.evalAdvancedQuery(query, ((orderby, orderdir),))
        devs = (x.getObject() for x in objects)
        mydict = {'columns':['Device', 'Prod State'], 'data':[]}
        for dev in devs:
            if not self.context.checkRemotePerm(ZEN_VIEW, dev): continue
            mydict['data'].append({
                'Device' : dev.getPrettyLink(),
                'Prod State' : dev.getProdState()
            })
            if len(mydict['data'])>=100:
                break
        return mydict


class WatchListPortletView(BrowserView):
    """
    Accepts a list of paths to Zope objects which it then attempts to resolve.
    If no list of paths is given, it will try to read them from the POST data
    of the REQUEST object.

    @param entities: A list of paths that should be resolved into objects
        and passed to L{getDashboardObjectsEventSummaryJSON}.
    @type entities: list
    @return: A JSON-formatted string representation of the columns and rows
        of the table
    @rtype: string
    """
    @nocache
    @formreq
    def __call__(self, *args, **kwargs):
        return self.getEntityListEventSummary(*args, **kwargs)

    @json
    def getEntityListEventSummary(self, entities=None):
        if entities is None:
            entities = []
        elif isinstance(entities, basestring):
            entities = [entities]
        def getob(e):
            e = str(e)
            try:
                if not e.startswith('/zport/dmd'):
                    bigdev = '/zport/dmd' + e
                obj = self.context.dmd.unrestrictedTraverse(bigdev)
            except (AttributeError, KeyError):
                obj = self.context.dmd.Devices.findDevice(e)
            if self.context.has_permission("View", obj): return obj
        entities = filter(lambda x:x is not None, map(getob, entities))
        return getDashboardObjectsEventSummary(
            self.context.dmd.ZenEventManager, entities)


class DeviceIssuesPortletView(BrowserView):
    """
    A list of devices with issues.
    """
    @nocache
    def __call__(self):
        return self.getDeviceIssuesJSON()

    @json
    def getDeviceIssuesJSON(self):
        """
        Get devices with issues in a form suitable for a portlet on the
        dashboard.

        @return: A JSON representation of a dictionary describing devices
        @rtype: "{
            'columns':['Device', "Events'],
            'data':[
                {'Device':'<a href=/>', 'Events':'<div/>'},
                {'Device':'<a href=/>', 'Events':'<div/>'},
            ]}"
        """
        mydict = {'columns':[], 'data':[]}
        mydict['columns'] = ['Device', 'Events']
        deviceinfo = self.getDeviceDashboard()
        for alink, pill in deviceinfo:
            mydict['data'].append({'Device':alink,
                                   'Events':pill})
        return mydict

    @zepConnectionError([])
    def getDeviceDashboard(self):
        """return device info for bad device to dashboard"""
        zep = getFacade('zep')
        manager = IGUIDManager(self.context.dmd)
        deviceSeverities = zep.getDeviceIssuesDict()
        zem = self.context.dmd.ZenEventManager

        devdata = []
        for uuid in deviceSeverities.keys():
            dev = manager.getObject(uuid)
            if dev and isinstance(dev, Device):
                if (not zem.checkRemotePerm(ZEN_VIEW, dev)
                    or dev.productionState < zem.prodStateDashboardThresh
                    or dev.priority < zem.priorityDashboardThresh):
                    continue
                alink = dev.getPrettyLink()
                try:
                    severities = deviceSeverities[uuid]
                    severities = dict((zep.getSeverityName(sev).lower(), counts) for (sev, counts) in severities.iteritems())
                    pill = getEventPillME(dev, severities=severities)
                except ServiceException:
                    continue
                evts = [alink,pill]
                devdata.append((evts, severities))
        devdata.sort(key=lambda x:(x[1]['critical'], x[1]['error'], x[1]['warning']), reverse=True)
        return [x[0] for x in devdata[:100]]


heartbeat_columns = ['Host', 'Daemon Process', 'Seconds Down']

class HeartbeatPortletView(BrowserView):
    """
    Heartbeat issues in YUI table form, for the dashboard portlet
    """
    @nocache
    def __call__(self):
        return self.getHeartbeatIssuesJSON()

    @zepConnectionError({'columns': heartbeat_columns, 'data':[]})
    @json
    def getHeartbeatIssuesJSON(self):
        """
        Get heartbeat issues in a form suitable for a portlet on the dashboard.

        @return: A JSON representation of a dictionary describing heartbeats
        @rtype: "{
            'columns':['Host', 'Daemon Process', 'Seconds Down'],
            'data':[
                {'Device':'<a href=/>', 'Daemon':'zenhub', 'Seconds':10}
            ]}"
        """
        data = getHeartbeatObjects(deviceRoot=self.context.dmd.Devices,
                keys=heartbeat_columns)
        return {'columns': heartbeat_columns, 'data': data}


class UserMessagesPortletView(BrowserView):
    """
    User messages in YUI table form, for the dashboard portlet.
    """
    @nocache
    @json
    def __call__(self):
        """
        Get heartbeat issues in a form suitable for a portlet on the dashboard.

        @return: A JSON representation of a dictionary describing heartbeats
        @rtype: "{
            'columns':['Host', 'Daemon Process', 'Seconds Down'],
            'data':[
                {'Device':'<a href=/>', 'Daemon':'zenhub', 'Seconds':10}
            ]}"
        """
        ICONS = ['/zport/dmd/img/agt_action_success-32.png',
                 '/zport/dmd/img/messagebox_warning-32.png',
                 '/zport/dmd/img/agt_stop-32.png']
        msgbox = messaging.IUserMessages(self.context)
        msgs = msgbox.get_messages()
        cols = ['Message']
        res = []
        for msg in msgs:
            res.append(dict(
                title = msg.title,
                imgpath = ICONS[msg.priority],
                body = msg.body,
                ago = relative_time(msg.timestamp),
                deletelink = msg.absolute_url_path() + '/delMsg'
            ))
        res.reverse()
        return { 'columns': cols, 'data': res }
