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
    def addNode(self, type, contextUid, id, posQuery=None):

        result = super(ServiceRouter, self).addNode(type, contextUid, id)
        if 'msg' in result:
            raise Exception(result['msg'])

        if type=='Class':
            newUid = result['nodeConfig']['uid']

            q = dict(limit=None, start=0, sort=None, dir=None, params=None,
                     uid=contextUid, criteria=())
            q.update(posQuery)
            if isinstance(q['params'], basestring):
                q['params'] = unjson(q['params'])

            allinfos = self.api.getList(**q)

            newIndex = None
            for iobj, pos in enumerate(allinfos):
                if iobj.uid == newUid:
                    newIndex = pos
                    break

            result['newIndex'] = newIndex
        return result

    def query(self, limit=None, start=None, sort=None, dir=None, params=None,
              history=False, uid=None, criteria=()):
        if uid is None:
            uid = self.context

        if isinstance(params, basestring):
            params = unjson(params)

        services = self.api.getList(limit, start, sort, dir, params, uid,
                                  criteria)

        disabled = not Zuul.checkPermission('Manage DMD')

        data = Zuul.marshal(services)
        return DirectResponse(services=data, totalCount=services.total,
                              hash=services.hash_, disabled=disabled)

    def getTree(self, id):
        tree = self.api.getTree(id)
        data = Zuul.marshal(tree)
        return data['children']

    def getOrganizerTree(self, id):
        tree = self.api.getOrganizerTree(id)
        data = Zuul.marshal(tree)
        if 'children' in data:
            return data['children']
        else:
            return {}

    def getInfo(self, uid, keys=None):
        service = self.api.getInfo(uid)
        data = Zuul.marshal(service, keys)
        disabled = not Zuul.checkPermission('Manage DMD')
        return {'data': data, 'disabled': disabled, 'success': True}

    def getParentInfo(self, uid, keys=None):
        service = self.api.getParentInfo(uid)
        data = Zuul.marshal(service, keys)
        disabled = not Zuul.checkPermission('Manage DMD')
        return {'data': data, 'disabled': disabled, 'success': True}

    @require('Manage DMD')
    def setInfo(self, **data):
        service = self.api.getInfo(data['uid'])
        Zuul.unmarshal(data, service)
        return {'success': True}

    def getDevices(self, uid, start=0, params=None, limit=50, sort='device',
                   dir='ASC'):
        if isinstance(params, basestring):
            params = unjson(params)
        devices = self.api.getDevices(uid, start=start, params=params,
                                      limit=limit, sort=sort, dir=dir)
        data = Zuul.marshal(devices)
        return {'data': data, 'success': True}

    def getEvents(self, uid, start=0, params=None, limit=50, sort='device',
                   dir='ASC'):
        if isinstance(params, basestring):
            params = unjson(params)
        events = self.api.getEvents(uid, start=start, params=params,
                                    limit=limit, sort=sort, dir=dir)
        data = Zuul.marshal(events)
        return {'data': data, 'success': True}

    def getInstances(self, uid, start=0, params=None, limit=50, sort='name',
                   order='ASC'):
        if isinstance(params, basestring):
            params = unjson(params)
        instances = self.api.getInstances(uid, start=start, params=params,
                                          limit=limit, sort=sort, dir=order)

        keys = ['description', 'device', 'locking', 'monitored', 'name',
                'status', 'uid']
        data = Zuul.marshal(instances, keys)
        return {'data': data, 'success': True}
