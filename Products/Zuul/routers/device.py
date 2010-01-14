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

from Products.ZenUtils.Ext import DirectRouter
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

    def getDevices(self, uid=None, start=0, params=None, limit=50, sort='device',
                   dir='ASC'):
        facade = self._getFacade()
        devices = facade.getDevices(uid, start, limit, sort, dir)
        count = facade.deviceCount(uid)
        keys = ['name', 'ipAddress', 'productionState', 'events', 'availability']
        data = Zuul.marshal(devices, keys)
        return {'devices': data, 'totalCount': count}

    def moveDevices(self, uids, target):
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

    def getEvents(self, uid):
        facade = self._getFacade()
        events = facade.getEvents(uid)
        data = Zuul.marshal(events)
        return {'data': data, 'success': True}

