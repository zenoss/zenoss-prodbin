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

from Products.ZenUtils.Ext import DirectRouter, DirectResponse
from Products import Zuul
from Products.ZenUtils.json import unjson

class ServiceRouter(DirectRouter):

    def __init__(self, context, request):
        super(ServiceRouter, self).__init__(context, request)
        self.api = Zuul.getFacade('service')

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

    def setInfo(self, **data):
        if not Zuul.checkPermission('Manage DMD'):
            raise Exception('You do not have permission to save changes.')
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
