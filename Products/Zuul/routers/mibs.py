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
"""
Operations for MIBs.

Available at:  /zport/dmd/mib_router
"""

import logging
from Products.ZenUtils.Ext import DirectResponse
from Products.Zuul.routers import TreeRouter
from Products.Zuul.decorators import require
from Products.Zuul.interfaces import IInfo
from Products.Zuul.form.interfaces import IFormBuilder
from Products import Zuul

log = logging.getLogger('zen.MibRouter')


class MibRouter(TreeRouter):
    """
    A JSON/ExtDirect interface to operations on MIBs
    """

    def __init__(self, context, request):
        self.api = Zuul.getFacade('mibs')
        self.context = context
        self.request = request
        super(MibRouter, self).__init__(context, request)

    def _getFacade(self):
        return self.api

    def getTree(self, id='/zport/dmd/Mibs'):
        """
        Returns the tree structure of an organizer hierarchy. Default tree
        root is MIBs.

        @type  id: string
        @param id: (optional) Id of the root node of the tree to be
                   returned (default: '/zport/dmd/Mibs')
        @rtype:   [dictionary]
        @return:  Object representing the tree
        """
        tree = self.api.getTree(id)
        data = Zuul.marshal(tree)
        return [data]

    def getOrganizerTree(self, id):
        """
        Returns the tree structure of an organizer hierarchy, only including
        organizers.

        @type  id: string
        @param id: Id of the root node of the tree to be returned
        @rtype:   [dictionary]
        @return:  Object representing the organizer tree
        """
        tree = self.api.getOrganizerTree(id)
        data = Zuul.marshal(tree)
        return [data]

    @require('Manage DMD')
    def addNode(self, contextUid='', id='', type=''):
        """
        Add an organizer or new blank MIB.

        @type  contextUid: string
        @param contextUid: Context to attach new node
        @type  id: string
        @param id: Id of the new orgainzer or blank MIB
        @type  type: string
        @param type: Type of new node. Can be 'organizer' or 'MIB'
        @rtype:   DirectResponse
        @return:  B{Properties}:
           - tree: ([dictionary]) Object representing the new tree
        """
        # GAH!  JS passes back a keyword of 'type'
        nodeType = type
        if nodeType not in ['organizer', 'MIB']:
            return DirectResponse.fail('Not creating "%s"' % nodeType)

        try:
            if nodeType == 'organizer':
                uid = contextUid + '/' + id
                maoUid = uid.replace('/zport/dmd', '')
                self.context.dmd.Mibs.manage_addOrganizer(maoUid)
                self.context.dmd.restrictedTraverse(uid)
            else:
                container = self.context.dmd.restrictedTraverse(contextUid)
                container.manage_addMibModule(id)

            return DirectResponse.succeed(tree=self.getTree())
        except Exception, e:
            return DirectResponse.fail(str(e))

    def addMIB(self, package, organizer='/'):
        """
        Add a new MIB by URL or local file.

        @type  package: string
        @param package: URL or local file path to MIB file
        @type  organizer: string
        @param organizer: ID of the organizer to add MIB to
        @rtype:   DirectResponse
        @return:  B{Properties}:
           - jobId: (string) ID of the add MIB job
        """
        facade = self._getFacade()
        success, message = facade.addMibPackage(package, organizer)
        if success:
            return DirectResponse.succeed(jobId=message)
        else:
            return DirectResponse.fail(message)

    @require('Manage DMD')
    def deleteNode(self, uid):
        """
        Remove an organizer or MIB.

        @type  uid: string
        @param uid: UID of organizer or MIB to remove
        @rtype:   DirectResponse
        @return:  B{Properties}:
           - tree: ([dictionary]) Object representing the new tree
        """
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
        Move an organizer or MIB from one organizer to another.

        @type  uids: [string]
        @param uids: UIDs of organizers and MIBs to move
        @type  target: string
        @param target: UID of the organizer to move to
        @rtype:   DirectResponse
        @return:  B{Properties}:
           - data: (dictionary) Object representing the new parent organizer
        """
        parent = self.api.moveMibs(uids, target)
        parent = IInfo(parent)
        return DirectResponse.succeed(data=Zuul.marshal(parent))

    def getInfo(self, uid, useFieldSets=True):
        """
        Get the properties of a MIB

        @type  uid: string
        @param uid: Unique identifier of a MIB
        @type  useFieldSets: boolean
        @param useFieldSets: True to return a fieldset version of the info form
                             (default: True)
        @rtype:   DirectResponse
        @return:  B{Properties}
            - data: (dictionary) Object representing a MIB's properties
            - form: (dictionary) Object representing an edit form for a MIB's
                    properties
        """
        facade = self._getFacade()
        info = facade.getInfo(uid)
        form = IFormBuilder(info).render(fieldsets=useFieldSets)
        return DirectResponse(success=True, data=Zuul.marshal(info), form=form)

    def setInfo(self, **data):
        """
        Set attributes on a MIB.
        This method accepts any keyword argument for the property that you wish
        to set. The only required property is "uid".

        @type    uid: string
        @keyword uid: Unique identifier of a MIB
        @rtype:   DirectResponse
        @return:  B{Properties}
            - data: (dictionary) Object representing a MIB's new properties
        """
        uid = data['uid']
        del data['uid']
        facade = self._getFacade()
        info = facade.setInfo(uid, data)
        return DirectResponse.succeed(data=Zuul.marshal(info))

    def getMibNodeTree(self, id=None):
        """
        A MIB node is a regular OID (ie you can hit it with snmpwalk)
        """
        if id is None:
            return []
        tree = self.api.getMibNodeTree(id)
        data = Zuul.marshal(tree)
        return [data]

    def getMibTrapTree(self, id=None):
        """
        A MIB trap node is an OID received from a trap
        """
        if id is None:
            return []
        tree = self.api.getMibTrapTree(id)
        data = Zuul.marshal(tree)
        return [data]

