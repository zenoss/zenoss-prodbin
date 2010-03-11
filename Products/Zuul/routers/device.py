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
from Products.ZenUtils.Ext import DirectResponse
from Products.ZenUtils.json import unjson
from Products import Zuul
from Products.Zuul.routers import TreeRouter
from Products.Zuul.form.interfaces import IFormBuilder

import logging
log = logging.getLogger('zen.Zuul')


class DeviceRouter(TreeRouter):

    def _getFacade(self):
        return Zuul.getFacade('device', self.context)

    def getTree(self, id):
        facade = self._getFacade()
        tree = facade.getTree(id)
        data = Zuul.marshal(tree)
        return data['children']

    def getComponents(self, uid=None, meta_type=None, keys=None, start=0, limit=50,
                      sort='name', dir='ASC'):
        facade = self._getFacade()
        comps = facade.getComponents(uid, meta_type=meta_type, start=start,
                                     limit=limit, sort=sort, dir=dir)
        return DirectResponse(data=Zuul.marshal(comps, keys=keys))

    def getComponentTree(self, uid=None, id=None):
        if id:
            uid=id
        facade = self._getFacade()
        data = facade.getComponentTree(uid)
        sevs = [c[0].lower() for c in
                self.context.ZenEventManager.severityConversions]
        data.sort(cmp=lambda a,b:cmp(sevs.index(a['severity']),
                                     sevs.index(b['severity'])))
        result = []
        for datum in data:
            result.append(dict(
                id=datum['type'],
                path='Components/%s' % datum['type'],
                text={
                    'text':datum['type'],
                    'count':datum['count'],
                    'description':'components'
                },
                iconCls='tree-severity-icon-small-'+datum['severity'],
                leaf=True
            ))
        return result

    def getForm(self, uid):
        info = self._getFacade().getInfo(uid)
        form = IFormBuilder(info).render()
        return DirectResponse(form=form)

    def getInfo(self, uid, keys=None):
        facade = self._getFacade()
        process = facade.getInfo(uid)
        data = Zuul.marshal(process, keys)
        disabled = not Zuul.checkPermission('Manage DMD')
        return DirectResponse(data=data, disabled=disabled)

    def setInfo(self, **data):
        facade = self._getFacade()
        if not Zuul.checkPermission('Manage DMD'):
            raise Exception('You do not have permission to save changes.')
        process = facade.getInfo(data['uid'])
        Zuul.unmarshal(data, process)
        return DirectResponse()

    def getDevices(self, uid=None, start=0, params=None, limit=50, sort='name',
                   dir='ASC'):
        facade = self._getFacade()
        if isinstance(params, basestring):
            params = unjson(params)
        devices = facade.getDevices(uid, start, limit, sort, dir, params)
        keys = ['name', 'ipAddress', 'productionState', 'events']
        data = Zuul.marshal(devices, keys)
        return DirectResponse(devices=data, totalCount=devices.total,
                              hash=devices.hash_)

    def moveDevices(self, uids, target, hashcheck, ranges=(), uid=None,
                    params=None, sort='name', dir='ASC'):
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)

        facade = self._getFacade()
        try:
            facade.moveDevices(uids, target)
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail('Failed to move devices.')
        else:
            target = '/'.join(target.split('/')[:4])
            tree = self.getTree(target)
            return DirectResponse.succeed(tree=tree)

    def lockDevices(self, uids, hashcheck, ranges=(), updates=False,
                    deletion=False, sendEvent=False, uid=None, params=None,
                    sort='name', dir='ASC'):
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)
        facade = self._getFacade()
        success = True
        try:
            facade.setLockState(uids, deletion=deletion, updates=updates,
                                sendEvent=sendEvent)
            if not deletion and not updates:
                message = "Unlocked %s devices."
            else:
                actions = []
                if deletion: actions.append('deletion')
                if updates: actions.append('updates')
                message = "Locked %%s devices from %s." % ' and '.join(actions)
            return DirectResponse.succeed(message)
            message = message % len(uids)
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail('Failed to lock devices.')

    def resetIp(self, uids, hashcheck, uid=None, ranges=(), params=None,
                sort='name', dir='ASC'):
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)
        facade = self._getFacade()
        try:
            for uid in uids:
                info = facade.getInfo(uid)
                info.ipAddress = '' # Set to empty causes DNS lookup
            return DirectResponse('Reset %s IP addresses.' % len(uids))
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail('Failed to reset IP addresses.')

    def resetCommunity(self, uids, hashcheck, uid=None, ranges=(), params=None,
                      sort='name', dir='ASC'):
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)
        facade = self._getFacade()
        try:
            for uid in uids:
                facade.resetCommunityString(uid)
            return DirectResponse('Reset %s community strings.' % len(uids))
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail('Failed to reset community strings.')

    def setProductionState(self, uids, prodState, hashcheck, uid=None,
                           ranges=(), params=None, sort='name', dir='ASC'):
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)
        facade = self._getFacade()
        try:
            for uid in uids:
                info = facade.getInfo(uid)
                info.productionState = prodState
            return DirectResponse()
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail('Failed to change production state.')

    def setPriority(self, uids, priority, hashcheck, uid=None, ranges=(),
                    params=None, sort='name', dir='ASC'):
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)
        facade = self._getFacade()
        try:
            for uid in uids:
                info = facade.getInfo(uid)
                info.priority = priority
            return DirectResponse('Set %s devices to %s priority.' % (
                len(uids), info.priority
            ))
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail('Failed to change priority.')

    def setCollector(self, uids, collector, hashcheck, uid=None, ranges=(),
                     params=None, sort='name', dir='ASC'):
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)
        facade = self._getFacade()
        try:
            for uid in uids:
                info = facade.getInfo(uid)
                info.collector = collector
            return DirectResponse('Changed collector to %s for %s devices.' %
                                  (collector, len(uids)))
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail('Failed to change the collector.')

    def removeDevices(self, uids, hashcheck, action="remove", uid=None,
                      ranges=(), params=None, sort='name', dir='ASC'):
        if ranges:
            uids += self.loadRanges(ranges, hashcheck, uid, params, sort, dir)
        facade = self._getFacade()
        try:
            if action=="remove":
                facade.removeDevices(uids, organizer=uid)
            elif action=="delete":
                facade.deleteDevices(uids)
            return DirectResponse.succeed(
                devtree = self.getTree('/zport/dmd/Devices'),
                grptree = self.getTree('/zport/dmd/Groups'),
                loctree = self.getTree('/zport/dmd/Locations')
            )
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail('Failed to remove devices.')

    def getEvents(self, uid):
        facade = self._getFacade()
        events = facade.getEvents(uid)
        data = Zuul.marshal(events)
        return DirectResponse(data=data)

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

    def getProductionStates(self):
        return [s.split(':') for s in self.context.dmd.prodStateConversions]

    def getPriorities(self):
        return [s.split(':') for s in self.context.dmd.priorityConversions]

    def getCollectors(self):
        return self.context.dmd.Monitors.getPerformanceMonitorNames()

