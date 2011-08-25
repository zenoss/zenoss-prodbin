###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
"""
Zenoss JSON API
"""

from Products.ZenUtils.Ext import DirectRouter, DirectResponse
from Products.Zuul.decorators import require
from Products.Zuul.marshalling import Marshaller
from Products import Zuul
import logging
log = logging.getLogger(__name__)


class TreeRouter(DirectRouter):
    """
    A common base class for routers that have a hierarchical tree structure.
    """

    @require('Manage DMD')
    def addNode(self, type, contextUid, id, description=None):
        """
        Add a node to the existing tree underneath the node specified
        by the context UID

        @type  type: string
        @param type: Either 'class' or 'organizer'
        @type  contextUid: string
        @param contextUid: Path to the node that will
                           be the new node's parent (ex. /zport/dmd/Devices)
        @type  id: string
        @param id: Identifier of the new node, must be unique in the
                   parent context
        @type  description: string
        @param description: (optional) Describes this new node (default: None)
        @rtype:   dictionary
        @return:  Marshaled form of the created node
        """
        result = {}
        try:
            facade = self._getFacade()
            if type.lower() == 'class':
                uid = facade.addClass(contextUid, id)
            else:
                organizer = facade.addOrganizer(contextUid, id, description)
                uid = organizer.uid

            treeNode = facade.getTree(uid)
            result['nodeConfig'] = Zuul.marshal(treeNode)
            result['success'] = True
        except Exception, e:
            log.exception(e)
            result['msg'] = str(e)
            result['success'] = False
        return result

    @require('Manage DMD')
    def deleteNode(self, uid):
        """
        Deletes a node from the tree.

        B{NOTE}: You can not delete a root node of a tree

        @type  uid: string
        @param uid: Unique identifier of the node we wish to delete
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - msg: (string) Status message
        """
        # make sure we are not deleting a root node
        if not self._canDeleteUid(uid):
            raise Exception('You cannot delete the root node')
        facade = self._getFacade()
        facade.deleteNode(uid)
        msg = "Deleted node '%s'" % uid
        return DirectResponse.succeed(msg=msg)

    def moveOrganizer(self, targetUid, organizerUid):
        """
        Move the organizer uid to be underneath the organizer
        specified by the targetUid.

        @type  targetUid: string
        @param targetUid: New parent of the organizer
        @type  organizerUid: string
        @param organizerUid: The organizer to move
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - data: (dictionary) Moved organizer
        """
        facade = self._getFacade()
        data = facade.moveOrganizer(targetUid, organizerUid)
        return DirectResponse.succeed(data=Zuul.marshal(data))

    def _getFacade(self):
        """
        Abstract method for child classes to use to get their facade
        """
        raise NotImplementedError("You must implement the _getFacade method")

    def asyncGetTree(self, id=None):
        """
        Server side method for asynchronous tree calls. Retrieves
        the immediate children of the node specified by "id"

        NOTE: our convention on the UI side is if we are asking
        for the root node then return the root and its children
        otherwise just return the children

        @type  id: string
        @param id: The uid of the node we are getting the children for
        @rtype:   [dictionary]
        @return:  Object representing the immediate children
        """
        facade = self._getFacade()
        currentNode = facade.getTree(id)
        # we want every tree property except the "children" one
        keys = ('id', 'path', 'uid', 'iconCls', 'text', 'hidden', 'leaf')
        children = []
        # explicitly marshall the children
        for child in currentNode.children:
            childData = Marshaller(child).marshal(keys)
            children.append(childData)
        obj = currentNode._object._unrestrictedGetObject()
        # check to see if we are asking for the root
        primaryId = obj.getDmdRoot(obj.dmdRootName).getPrimaryId()
        if id == primaryId:
            root = Marshaller(currentNode).marshal(keys)
            root['children'] = children
            return [root]
        return children

    def _canDeleteUid(self, uid):
        """
        We can not delete top level UID's. For example:
            - '/zport/dmd/Processes' this will return False (we can NOT delete)
            - '/zport/dmd/Processes/Child' will return True
                (we can delete this)
        """
        # check the number of levels deep it is
        levels = len(uid.split('/'))
        return levels > 4
