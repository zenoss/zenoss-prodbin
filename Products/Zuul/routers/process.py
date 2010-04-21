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
from Products.Zuul.decorators import require
from Products.Zuul.routers import TreeRouter
from Products.ZenUtils.Ext import DirectResponse

class ProcessRouter(TreeRouter):

    def _getFacade(self):
        return Zuul.getFacade('process', self.context)

    def getTree(self, id):
        facade = self._getFacade()
        tree = facade.getTree(id)
        data = Zuul.marshal(tree)
        return [data]

    def moveProcess(self, uid, targetUid):
        facade = self._getFacade()
        primaryPath = facade.moveProcess(uid, targetUid)
        id = '.'.join(primaryPath)
        uid = '/'.join(primaryPath)
        return DirectResponse.succeed(uid=uid, id=id)

    def getInfo(self, uid, keys=None):
        facade = self._getFacade()
        process = facade.getInfo(uid)
        data = Zuul.marshal(process, keys)
        return DirectResponse.succeed(data=data)

    @require('Manage DMD')
    def setInfo(self, **data):
        facade = self._getFacade()
        process = facade.getInfo(data['uid'])
        return DirectResponse.succeed(data=Zuul.unmarshal(data, process))

    def getDevices(self, uid, start=0, params=None, limit=50, sort='device',
                   dir='ASC'):
        facade = self._getFacade()
        devices = facade.getDevices(uid)
        data = Zuul.marshal(devices)
        return DirectResponse.succeed(data=data)

    def getEvents(self, uid):
        facade = self._getFacade()
        events = facade.getEvents(uid)
        data = Zuul.marshal(events)
        return DirectResponse.succeed(data=data)

    def getInstances(self, uid, start=0, params=None, limit=50, sort='name',
                     dir='ASC'):
        facade = self._getFacade()
        instances = facade.getInstances(uid, start, limit, sort, dir, params)
        data = Zuul.marshal(instances)
        return DirectResponse.succeed(data=data, total=instances.total)

    def getSequence(self):
        facade = self._getFacade()
        sequence = facade.getSequence()
        data = Zuul.marshal(sequence)
        return DirectResponse.succeed(data=data)

    def setSequence(self, uids):
        facade = self._getFacade()
        facade.setSequence(uids)
        return DirectResponse.succeed()
