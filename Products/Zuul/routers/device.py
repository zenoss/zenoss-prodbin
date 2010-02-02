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

from itertools import islice

from Products.ZenUtils.Ext import DirectRouter
from Products.ZenUtils.json import unjson
from Products import Zuul

class DeviceRouter(DirectRouter):

    def _getFacade(self):
        return Zuul.getFacade('device')

    def getTree(self, id):
        facade = self._getFacade()
        tree = facade.getTree(id)
        data = Zuul.marshal(tree)
        return data['children']

    def getInfo(self, uid, keys=None):
        facade = self._getFacade()
        process = facade.getInfo(uid)
        data = Zuul.marshal(process, keys)
        disabled = not Zuul.checkPermission('Manage DMD')
        return {'data': data, 'disabled': disabled, 'success': True}

    def setInfo(self, **data):
        facade = self._getFacade()
        if not Zuul.checkPermission('Manage DMD'):
            raise Exception('You do not have permission to save changes.')
        process = facade.getInfo(data['uid'])
        Zuul.unmarshal(data, process)
        return {'success': True}

    def getDevices(self, uid=None, start=0, params=None, limit=50, sort='name',
                   dir='ASC'):
        facade = self._getFacade()
        if isinstance(params, basestring):
            params = unjson(params)
        devices = facade.getDevices(uid, start, limit, sort, dir, params)
        keys = ['name', 'ipAddress', 'productionState', 'events']
        data = Zuul.marshal(devices, keys)
        return {'devices': data,
                'totalCount': devices.total,
                'hash': devices.hash_}

    def moveDevices(self, uids, target, hashcheck, ranges=(), uid=None,
                    params=None, sort='name', dir='ASC'):
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)

        facade = self._getFacade()
        try:
            facade.moveDevices(uids, target)
        except:
            return {'success': False}
        else:
            success = True
            target = '/'.join(target.split('/')[:4])
            tree = self.getTree(target)
            return {'success':success, 'tree':tree}

    def removeDevices(self, uids, hashcheck, action="remove", uid=None,
                      ranges=(), params=None, sort='name', dir='ASC'):
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)
        facade = self._getFacade()
        success = False
        try:
            if action=="remove":
                facade.removeDevices(uids, organizer=uid)
            elif action=="delete":
                facade.deleteDevices(uids)
        except:
            success = False
        else:
            success = True
        return {
            'success': success,
            'devtree': self.getTree('/zport/dmd/Devices'),
            'grptree': self.getTree('/zport/dmd/Groups'),
            'loctree': self.getTree('/zport/dmd/Locations')
        }

    def getEvents(self, uid):
        facade = self._getFacade()
        events = facade.getEvents(uid)
        data = Zuul.marshal(events)
        return {'data': data, 'success': True}

    def loadRanges(self, ranges, hashcheck, uid=None, params=None,
                      sort='name', dir='ASC'):
        facade = self._getFacade()
        if isinstance(params, basestring):
            params = unjson(params)
        devs = facade.getDevices(uid, sort=sort, dir=dir, params=params,
                                 hashcheck=hashcheck)
        uids = []
        for start, stop in sorted(ranges):
            uids.extend(b.uid for b in islice(devs, start, stop))
        return uids

    def getUserCommands(self, uid):
        facade = self._getFacade()
        cmds = facade.getUserCommands(uid)
        return Zuul.marshal(cmds, ['id', 'description'])
