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
from Products.Zuul.decorators import require

class ProcessRouter(DirectRouter):

    def _getFacade(self):
        return Zuul.getFacade('process')

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

    @require('Manage DMD')
    def setInfo(self, **data):
        facade = self._getFacade()
        process = facade.getInfo(data['uid'])
        Zuul.unmarshal(data, process)
        return {'success': True}

    @require('Manage DMD')
    def addNode(self, type, contextUid, id):
        facade = self._getFacade()
        if type.lower() == 'organizer':
            uid = facade.addOrganizer(contextUid, id)
            msg = "Added organizer '%s'" % id
        else:
            uid = facade.addClass(contextUid, id)
            msg = "Added class '%s'" % id
        treeNode = facade.getTree(uid)
        nodeConfig = Zuul.marshal(treeNode)
        return {'success': True, 'msg': msg, 'nodeConfig': nodeConfig}

    @require('Manage DMD')
    def deleteNode(self, uid):
        if uid == '/zport/dmd/Processes':
            raise Exception('You cannot delete the root node')
        facade = self._getFacade()
        facade.deleteNode(uid)
        msg = "Deleted node '%s'" % uid
        return {'success': True, 'msg': msg}

    def getDevices(self, uid, start=0, params=None, limit=50, sort='device',
                   dir='ASC'):
        facade = self._getFacade()
        devices = facade.getDevices(uid)
        data = Zuul.marshal(devices)
        return {'data': data, 'success': True}

    def getEvents(self, uid):
        facade = self._getFacade()
        events = facade.getEvents(uid)
        data = Zuul.marshal(events)
        return {'data': data, 'success': True}

