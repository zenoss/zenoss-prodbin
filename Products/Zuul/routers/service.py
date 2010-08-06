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

from Products import Zuul
from Products.Zuul.routers import TreeRouter
from Products.Zuul.decorators import require
from Products.ZenUtils.Ext import DirectResponse
from Products.ZenUtils.jsonutils import unjson

class ServiceRouter(TreeRouter):

    def __init__(self, context, request):
        self.api = Zuul.getFacade('service')
        self.context = context
        self.request = request
        super(ServiceRouter, self).__init__(context, request)

    def _getFacade(self):
        return self.api

    def _canDeleteUid(self,uid):
        # check the number of levels deep it is
        levels = len(uid.split('/'))
        return levels > 5

    @require('Manage DMD')
    def addClass(self, contextUid, id, posQuery=None):
        newUid = self.api.addClass(contextUid, id)
        if isinstance(posQuery.get('params'), basestring):
            posQuery['params'] = unjson(posQuery['params'])
        result = self.api.getList(**posQuery)
        for count, serviceInfo in enumerate(result['serviceInfos']):
            if serviceInfo.uid == newUid:
                newIndex = count
                break
        else:
            raise Exception('The new service was added, but the system was '
                            'unable to add it to the list.')
        return DirectResponse(newIndex=newIndex)

    def query(self, limit=None, start=None, sort=None, dir=None, params=None,
              history=False, uid=None, criteria=()):
        if uid is None:
            uid = self.context

        if isinstance(params, basestring):
            params = unjson(params)

        services = self.api.getList(limit, start, sort, dir, params, uid,
                                  criteria)

        disabled = not Zuul.checkPermission('Manage DMD')

        data = Zuul.marshal(services['serviceInfos'])
        return DirectResponse(services=data, totalCount=services['total'],
                              hash=services['hash'], disabled=disabled)

    def getTree(self, id):
        tree = self.api.getTree(id)
        data = Zuul.marshal(tree)
        return [data]

    def getOrganizerTree(self, id):
        tree = self.api.getOrganizerTree(id)
        data = Zuul.marshal(tree)
        return [data]

    def getInfo(self, uid, keys=None):
        service = self.api.getInfo(uid)
        data = Zuul.marshal(service, keys)
        disabled = not Zuul.checkPermission('Manage DMD')
        return DirectResponse.succeed(data=data, disabled=disabled)

    def getParentInfo(self, uid, keys=None):
        service = self.api.getParentInfo(uid)
        data = Zuul.marshal(service, keys)
        disabled = not Zuul.checkPermission('Manage DMD')
        return DirectResponse.succeed(data=data, disabled=disabled)

    def getClassNames(self, uid=None, query=None):
        data = self.api.getClassNames(uid, query)
        return DirectResponse.succeed(data=data)

    @require('Manage DMD')
    def setInfo(self, **data):
        service = self.api.getInfo(data['uid'])
        if data.has_key('serviceKeys') and isinstance(data['serviceKeys'], str):
            data['serviceKeys'] = \
                    tuple([l.strip() for l in data['serviceKeys'].split(',')])
        Zuul.unmarshal(data, service)
        return DirectResponse.succeed()

    def getDevices(self, uid, start=0, params=None, limit=50, sort='device',
                   dir='ASC'):
        if isinstance(params, basestring):
            params = unjson(params)
        devices = self.api.getDevices(uid, start=start, params=params,
                                      limit=limit, sort=sort, dir=dir)
        data = Zuul.marshal(devices)
        return DirectResponse.succeed(data=data)

    def getEvents(self, uid, start=0, params=None, limit=50, sort='device',
                   dir='ASC'):
        if isinstance(params, basestring):
            params = unjson(params)
        events = self.api.getEvents(uid, start=start, params=params,
                                    limit=limit, sort=sort, dir=dir)
        data = Zuul.marshal(events)
        return DirectResponse.succeed(data=data)

    def getInstances(self, uid, start=0, params=None, limit=50, sort='name',
                   dir='ASC'):
        if isinstance(params, basestring):
            params = unjson(params)
        instances = self.api.getInstances(uid, start=start, params=params,
                                          limit=limit, sort=sort, dir=dir)

        keys = ['description', 'device', 'locking', 'monitored', 'name',
                'status', 'uid']
        data = Zuul.marshal(instances, keys)
        return DirectResponse.succeed(data=data, totalCount=instances.total)

    @require('Manage DMD')
    def moveServices(self, sourceUids, targetUid):
        self.api.moveServices(sourceUids, targetUid)
        return DirectResponse.succeed()

    def getUnmonitoredStartModes(self, uid):
        data = self.api.getUnmonitoredStartModes(uid)
        return DirectResponse.succeed(data=Zuul.marshal(data))

    def getMonitoredStartModes(self, uid):
        data = self.api.getMonitoredStartModes(uid)
        return DirectResponse.succeed(data=Zuul.marshal(data))
