###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import logging
from Products.ZenUtils.Ext import DirectResponse
from Products.Zuul.routers import TreeRouter
from Products.Zuul.decorators import require
from Products.Zuul.interfaces import IInfo
from Products.Zuul.form.interfaces import IFormBuilder
from Products import Zuul

log = logging.getLogger('zen.MibRouter')


class MibRouter(TreeRouter):
    def __init__(self, context, request):
        self.api = Zuul.getFacade('mibs')
        self.context = context
        self.request = request
        super(MibRouter, self).__init__(context, request)

    def _getFacade(self):
        return self.api

    def getTree(self, id='/zport/dmd/Mibs'):
        tree = self.api.getTree(id)
        data = Zuul.marshal(tree)
        return [data]

    def getOrganizerTree(self, id):
        tree = self.api.getOrganizerTree(id)
        data = Zuul.marshal(tree)
        return [data]

    @require('Manage DMD')
    def addNode(self, contextUid='', id='', type=''):
        # GAH!  JS passes back a keyword of 'type'
        nodeType = type
        if nodeType not in ['organizer', 'MIB']:
            return DirectResponse.fail('Not creating "%s"' % nodeType)

        try:
            if nodeType == 'organizer':
                uid = contextUid + '/' + id
                maoUid = uid.replace('/zport/dmd', '')
                self.context.dmd.Mibs.manage_addOrganizer(maoUid)
                represented = self.context.dmd.restrictedTraverse(uid)
            else:
                container = self.context.dmd.restrictedTraverse(contextUid)
                represented = container.manage_addMibModule(id)

            return DirectResponse.succeed(tree=self.getTree())
        except Exception, e:
            return DirectResponse.fail(str(e))

    def addMIB(self, package, organizer='/'):
        facade = self._getFacade()
        success, message = facade.addMibPackage(package, organizer)
        if success:
            return DirectResponse.succeed(jobId=message)
        else:
            return DirectResponse.fail(message)

    @require('Manage DMD')
    def deleteNode(self, uid):
        represented = self.context.dmd.restrictedTraverse(uid)
        organizer = represented.getParentNode()
        if represented.meta_type == 'MibOrganizer':
            organizer.manage_deleteOrganizer(represented.id)
        else:
            organizer.removeMibModules(ids=represented.id)
        return DirectResponse.succeed(tree=self.getTree())

    @require('Manage DMD')
    def moveNode(self, uids, target):
        """
        Move a node from its current organizer to another.
        """
        parent = self.api.moveMibs(uids, target)
        parent = IInfo(parent)
        return DirectResponse.succeed(data=Zuul.marshal(parent))

    def oldMoveNode(self, uids, target):
        for uid in uids:
            represented = self.context.dmd.restrictedTraverse(uid)
            organizer = represented.getParentNode()
            organizer.moveMibModules(target, ids=represented.id)
            representedNode = self._createTreeNode(represented)
        return DirectResponse.succeed(tree=self.getTree(),
                newNode=representedNode)

    def getInfo(self, uid, useFieldSets=True):
        """
        @returns the details of a single info object as well as the form describing its schema
        """
        facade = self._getFacade()
        info = facade.getInfo(uid)
        form = IFormBuilder(info).render(fieldsets=useFieldSets)
        return DirectResponse(success=True, data=Zuul.marshal(info), form=form)

    def setInfo(self, **data):
        uid = data['uid']
        del data['uid']
        facade = self._getFacade()
        info = facade.setInfo(uid, data)
        return DirectResponse.succeed(data=Zuul.marshal(info))
