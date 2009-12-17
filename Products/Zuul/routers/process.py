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

class ProcessRouter(DirectRouter):

    def _getFacade(self):
        return Zuul.getFacade('process')

    def getTree(self, id):
        facade = self._getFacade()
        tree = facade.getTree(id)
        data = Zuul.marshal(tree)
        return data['children']

    def getInfo(self, id, keys=None):
        facade = self._getFacade()
        process = facade.getInfo(id)
        data = Zuul.marshal(process, keys)
        disabled = not Zuul.checkPermission('Manage DMD')
        return {'data': data, 'disabled': disabled, 'success': True}

    def setInfo(self, **data):
        facade = self._getFacade()
        if not Zuul.checkPermission('Manage DMD'):
            raise Exception('You do not have permission to save changes.')
        process = facade.getInfo(data['id'])
        Zuul.unmarshal(data, process)
        return {'success': True}

    def getDevices(self, id):
        facade = self._getFacade()
        devices = facade.getDevices(id)
        data = []
        for device in devices:
            data.append(Zuul.marshal(device))
        return {'data': data, 'success': True}

    def getEvents(self, id):
        facade = self._getFacade()
        events = facade.getEvents(id)
        data = []
        for event in events:
            data.append(Zuul.marshal(event))
        return {'data': data, 'success': True}
