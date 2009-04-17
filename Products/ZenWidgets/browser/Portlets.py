###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import re
import simplejson

from Products.Five.browser import BrowserView
from Products.AdvancedQuery import Eq, Or

from Products.ZenUtils.Utils import relative_time
from Products.ZenUtils.json import json
from Products.ZenUtils.Utils import formreq, extractPostContent
from Products.ZenWidgets import messaging
from Products.ZenModel.ZenossSecurity import *
from Products.ZenEvents.browser.EventPillsAndSummaries import \
                                   getDashboardObjectsEventSummary, \
                                   ObjectsEventSummary,    \
                                   getEventPillME


class TopLevelOrganizerPortletView(ObjectsEventSummary):
    """
    Return JSON event summaries for a root organizer.
    """
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
        if type(prodStates)==type(''):
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
        mydict['data'] = mydict['data'][:100]
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

    def getDeviceDashboard(self):
        """return device info for bad device to dashboard"""
        zem = self.context.dmd.ZenEventManager
        devices = [d[0] for d in zem.getDeviceIssues(
                            severity=4, state=1)]
        devdata = []
        devclass = zem.getDmdRoot("Devices")
        getcolor = re.compile(r'class=\"evpill-(.*?)\"', re.S|re.I|re.M).search
        colors = "red orange yellow blue grey green".split()
        def pillcompare(a,b):
            a, b = map(lambda x:getcolor(x[1]), (a, b))
            def getindex(x):
                try: 
                    color = x.groups()[0]
                    smallcolor = x.groups()[0].replace('-acked','')
                    isacked = 'acked' in color
                    index = colors.index(x.groups()[0].replace('-acked',''))
                    if isacked: index += .5
                    return index
                except: return 5
            a, b = map(getindex, (a, b))
            return cmp(a, b)
        for devname in devices:
            dev = devclass.findDevice(devname)
            if dev and dev.id == devname:
                if (not zem.checkRemotePerm(ZEN_VIEW, dev)
                    or dev.productionState < zem.prodStateDashboardThresh
                    or dev.priority < zem.priorityDashboardThresh):
                    continue
                alink = dev.getPrettyLink()
                try:
                    pill = getEventPillME(zem, dev)[0]
                except IndexError:
                    continue
                evts = [alink,pill]
                devdata.append(evts)
        devdata.sort(pillcompare)
        return devdata[:100]


class HeartbeatPortletView(BrowserView):
    """
    Heartbeat issues in YUI table form, for the dashboard portlet
    """
    def __call__(self):
        return self.getHeartbeatIssuesJSON()

    @json
    def getHeartbeatIssuesJSON(self):
        """
        Get heartbeat issues in a form suitable for a portlet on the dashboard.

        @return: A JSON representation of a dictionary describing heartbeats
        @rtype: "{
            'columns':['Device', 'Daemon', 'Seconds'],
            'data':[
                {'Device':'<a href=/>', 'Daemon':'zenhub', 'Seconds':10}
            ]}"
        """
        mydict = {'columns':[], 'data':[]}
        mydict['columns'] = ['Device', 'Daemon', 'Seconds']
        heartbeats = self.context.dmd.ZenEventManager.getHeartbeat()
        for Device, Daemon, Seconds, dummy in heartbeats:
            mydict['data'].append({'Device':Device,
                'Daemon':Daemon, 'Seconds':Seconds})
        return mydict


class UserMessagesPortletView(BrowserView):
    """
    User messages in YUI table form, for the dashboard portlet.
    """
    @json
    def __call__(self):
        """
        Get heartbeat issues in a form suitable for a portlet on the dashboard.

        @return: A JSON representation of a dictionary describing heartbeats
        @rtype: "{
            'columns':['Device', 'Daemon', 'Seconds'],
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


