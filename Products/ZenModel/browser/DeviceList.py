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

from Products.Five.browser import BrowserView
from Products.ZenModel.DeviceOrganizer import DeviceOrganizer
from Products.ZenUtils.json import json
from Products.ZenUtils.Utils import formreq, unused, ipsort
from Products.AdvancedQuery import MatchRegexp, Or, Eq, In
from Products.ZenUtils.FakeRequest import FakeRequest

class DeviceList(BrowserView):
    """
    Populates the device list.
    """
    @formreq
    def __call__(self, *args, **kwargs):
        return self._getJSONDeviceInfo(*args, **kwargs)

    @json
    def _getJSONDeviceInfo(self, offset=0, count=50, filter='',
                           orderby='id', orderdir='asc'):
        """
        Get devices under self according to criteria and return results as
        JSON.

        @return: A JSON representation of a tuple containing a list of lists of
        device info, and the total number of matching devices
        @rtype: "([[a, b, c], [a, b, c]], 17)"
        """
        totalCount, devicelist = self._getAdvancedQueryDeviceList(
                offset, count, filter, orderby, orderdir)
        obs = [x.getObject() for x in devicelist]
        if orderby=='getDeviceIp':
            obs.sort(lambda a,b:ipsort(a.getDeviceIp(), b.getDeviceIp()))
        if orderdir=='desc': obs.reverse()
        results = [ob.getDataForJSON() + ['odd'] for ob in obs]
        return results, totalCount

    def _getAdvancedQueryDeviceList(self, offset=0, count=50, filter='',
                                   orderby='id', orderdir='asc'):
        """
        Ask the catalog for devices matching the criteria specified.
        """
        context = self.context
        if not isinstance(context, DeviceOrganizer):
            context = self.context.dmd.Devices
        catalog = getattr(context, context.default_catalog)
        filter = '(?is).*%s.*' % filter
        filterquery = Or(
            MatchRegexp('id', filter),
            MatchRegexp('getDeviceIp', filter),
            MatchRegexp('getProdState', filter),
            MatchRegexp('getDeviceClassPath', filter)
        )
        query = Eq('getPhysicalPath', context.absolute_url_path()
                    ) & filterquery
        objects = catalog.evalAdvancedQuery(query, ((orderby, orderdir),))
        objects = list(objects)
        totalCount = len(objects)
        offset, count = int(offset), int(count)
        obs = objects[offset:offset+count]
        return totalCount, obs


class DeviceBatch(BrowserView):
    """
    Given various criteria, figure out what devices are relevant and execute
    the action specified.
    """
    @formreq
    def __call__(self, *args, **kwargs):
        return self._setDeviceBatchProps(*args, **kwargs)

    @property
    def id(self):
        """
        This can appear in the acquisition chain, and ZenModelBase.getDmd needs
        an id attribute.
        """
        return self.context.id

    def _setDeviceBatchProps(self, method='', extraarg=None,
                            selectstatus='none', goodevids=[],
                            badevids=[], offset=0, count=50, filter='',
                            orderby='id', orderdir='asc', REQUEST=None,
                             **kwargs):
        if not method: return self()
        d = {'lockDevicesFromUpdates':'sendEventWhenBlocked',
             'lockDevicesFromDeletion':'sendEventWhenBlocked',
             'unlockDevices':'',
             'setGroups':'groupPaths',
             'setSystems':'systemPaths',
             'setLocation':'locationPath',
             'setPerformanceMonitor':'performanceMonitor',
             'moveDevices':'moveTarget',
             'removeDevices':('deleteStatus', 'deleteHistory', 'deletePerf'),
             'setProdState':'state',
             'setPriority':'priority'
            }
        request = FakeRequest()
        argdict = dict(REQUEST=request)
        if d[method]:
            if type(d[method]) in [tuple, list]:
                for argName in d[method]:
                    argdict[argName] = self.request.get(argName, None)
            else:
                argdict[d[method]] = extraarg
        action = getattr(self.context, method)
        argdict['deviceNames'] = self._getDeviceBatch(selectstatus,
                                  goodevids, badevids, offset, count,
                                  filter, orderby, orderdir)
        # This will call the method on the context, which will redirect to a
        # new (or the same) screen and set a message
        return action(**argdict)

    def _getDeviceBatch(self, selectstatus='none', goodevids=[],
                       badevids=[], offset=0, count=50, filter='',
                       orderby='id', orderdir='asc'):
        unused(count, offset, orderby, orderdir)
        if not isinstance(goodevids, (list, tuple)):
            goodevids = [goodevids]
        if not isinstance(badevids, (list, tuple)):
            badevids = [badevids]
        if selectstatus=='all':
            idquery = ~In('id', badevids)
        else:
            idquery = In('id', goodevids)
        filter = '(?is).*%s.*' % filter
        filterquery = Or(
            MatchRegexp('id', filter),
            MatchRegexp('getDeviceIp', filter),
            MatchRegexp('getProdState', filter),
            MatchRegexp('getDeviceClassPath', filter)
        )
        query = Eq('getPhysicalPath', self.context.absolute_url_path()) & idquery
        query = query & filterquery
        catalog = getattr(self.context, self.context.default_catalog)
        objects = catalog.evalAdvancedQuery(query)
        return [x['id'] for x in objects]

