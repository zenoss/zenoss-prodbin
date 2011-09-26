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
Operations for Reports.

Available at:  /zport/dmd/report_router
"""

import logging
from itertools import izip_longest
from Products.ZenUtils.Ext import DirectRouter, DirectResponse
from Products.Zuul.decorators import require
from Products.Zuul.marshalling import Marshaller
from Products.Zuul.utils import ZuulMessageFactory as _t
from Products import Zuul
from Products.ZenMessaging.actions import sendUserAction
from Products.ZenMessaging.actions.constants import ActionTargetType, ActionName


log = logging.getLogger('zen.ReportRouter')

reportTypes = [
    'customDeviceReport',
    'graphReport',
    'multiGraphReport',
]

menuText = [
    _t('Custom Device Report'),
    _t('Graph Report'),
    _t('Multi-Graph Report'),
]

essentialReportOrganizers = [
    '/zport/dmd/Reports/Custom Device Reports',
    '/zport/dmd/Reports/Graph Reports',
    '/zport/dmd/Reports/Multi-Graph Reports',
    '/zport/dmd/Reports',
]

class ReportRouter(DirectRouter):
    """
    A JSON/ExtDirect interface to operations on reports
    """


    def __init__(self, context, request):
        self.api = Zuul.getFacade('reports')
        self.context = context
        self.request = request
        self.keys = ('id', 'path', 'uid', 'iconCls', 'text', 'hidden', 'leaf',
                'deletable', 'edit_url')
        super(ReportRouter, self).__init__(context, request)

    def _getFacade(self):
        return self.api

    def getTree(self, id):
        """
        Returns the tree structure of an organizer hierarchy where
        the root node is the organizer identified by the id parameter.

        @type  id: string
        @param id: Id of the root node of the tree to be returned
        @rtype:   [dictionary]
        @return:  Object representing the tree
        """
        facade = self._getFacade()
        tree = facade.getTree(id)
        data = Zuul.marshal(tree)
        return [data]

    def getReportTypes(self):
        """
        Get the available report types.

        @rtype:   DirectResponse
        @return:  B{Properties}:
           - menuText: ([string]) Human readable list of report types
           - reportTypes: ([string]) A list of the available report types
        """
        return DirectResponse.succeed(reportTypes=reportTypes,
                menuText=menuText)

    def asyncGetTree(self, id=None):
        children = self._getFacade().getTree(id).children
        return [Marshaller(child).marshal(self.keys) for child in children]

    @require('Manage DMD')
    def addNode(self, nodeType, contextUid, id):
        """
        Add a new report or report organizer.

        @type  nodeType: string
        @param nodeType: Type of new node. Can either be 'organizer' or one of
                         the report types returned from getReportTypes()
        @type  contextUid: string
        @param contextUid: The organizer where the new node should be added
        @type  id: string
        @param id: The new node's ID
        @rtype:   DirectResponse
        @return:  B{Properties}:
           - tree: (dictionary) Object representing the new Reports tree
           - newNode: (dictionary) Object representing the added node
        """
        facade = self._getFacade()
        if nodeType in reportTypes:
            facade.addReport(nodeType, contextUid, id)
            if sendUserAction:
                uid = contextUid + '/' + id
                sendUserAction(ActionTargetType.Report, ActionName.Add,
                               report=uid, reporttype=nodeType)
        else:
            facade.addOrganizer(contextUid, id, None)
            if sendUserAction:
                uid = contextUid + '/' + id
                sendUserAction(ActionTargetType.Organizer, ActionName.Add,
                               organizer=uid)

        return self._getTreeUpdates(contextUid, id)

    @require('Manage DMD')
    def deleteNode(self, uid):
        """
        Remove a report or report organizer.

        @type  uid: string
        @param uid: The UID of the node to delete
        @rtype:   [dictionary]
        @return:  B{Properties}:
           - tree: (dictionary) Object representing the new Reports tree
        """
        # make sure we are not deleting a required node
        if uid in essentialReportOrganizers:
            raise Exception('You cannot delete this organizer')
        self._getFacade().deleteNode(uid)
        contextUid = '/'.join(uid.split('/')[:-1])
        if sendUserAction:
            sendUserAction(ActionTargetType.Report, ActionName.Delete,
                           report=uid)
        return self._getTreeUpdates(contextUid)

    def _getTreeUpdates(self, contextUid, newId=None):
        marshalled = self._marshalPath(contextUid, newId)
        for parent, child in zip(marshalled[:-1], marshalled[1:]):
            parent['children'] = [child]
        result = {'tree': [marshalled[0]]}
        if newId:
            result['newNode'] = marshalled[-1]
        return DirectResponse.succeed(**result)

    @require('Manage DMD')
    def moveNode(self, uid, target):
        """
        Move a report or report organizer from one organizer to another.

        @type  uid: string
        @param uid: The UID of node to move
        @type  target: string
        @param target: The UID of the target Report organizer
        @rtype:   [dictionary]
        @return:  B{Properties}:
           - tree: (dictionary) Object representing the new Reports tree
           - newNode: (dictionary) Object representing the moved node
        """
        self._getFacade().moveNode(uid, target)
        if sendUserAction:
            sendUserAction(ActionTargetType.Report, ActionName.Move,
                           report=uid, target=target)
        return self._treeMoveUpdates(uid, target)

    def _treeMoveUpdates(self, uid, target):
        oldPathTokens = uid.split('/')
        oldPath = '/'.join(oldPathTokens[:-1])
        oldBranch = self._marshalPath(oldPath)
        newId = oldPathTokens[-1]
        newBranch = self._marshalPath(target, newId)
        for newParent, newChild, oldParent, oldChild in izip_longest(newBranch[:-1], newBranch[1:], oldBranch[:-1], oldBranch[1:], fillvalue=None):
            if newParent and oldParent and newParent['id'] != oldParent['id']:
                newParent['children'] = [newChild]
                oldParent['children'] = [oldChild]
            else:
                parent = newParent if newParent else oldParent
                if newChild and oldChild and newChild['id'] != oldChild['id']:
                    parent['children'] = [oldChild, newChild]
                else:
                    child = newChild if newChild else oldChild
                    parent['children'] = [child]
        tree = [newBranch[0]]
        if oldBranch[0]['id'] != newBranch[0]['id']:
            tree.append(oldBranch[0])
        newNode = newBranch[-1]
        return DirectResponse.succeed(tree=tree, newNode=newNode)

    def _marshalPath(self, contextUid, newId=None):
        tokens = contextUid.split('/')
        if newId:
            tokens.append(newId)
        paths = []
        # ["", "zport", "dmd", "Reports", <new node or an ancestor, at 4>, ...]
        for x in range(4, len(tokens) + 1):
            paths.append('/'.join(tokens[:x]))
        nodes = [self._getFacade().getTree(id) for id in paths]
        return [Marshaller(node).marshal(self.keys) for node in nodes]

