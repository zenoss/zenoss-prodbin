##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


"""
Zenoss JSON API
"""

from Products.ZenUtils.Ext import DirectRouter, DirectResponse
from Products.Zuul.decorators import require
from Products.Zuul.interfaces.tree import ICatalogTool
from Products.Zuul.marshalling import Marshaller
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenMessaging.audit import audit
from Products.ZenUtils.Utils import getDisplayType
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
                audit('UI.Class.Add', uid)
            else:
                organizer = facade.addOrganizer(contextUid, id, description)
                uid = organizer.uid
                audit(['UI', getDisplayType(organizer), 'Add'], organizer)

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
        node = facade._getObject(uid)

        # Audit first so it can display details like "name" while they exist.
        # Trac #29148: When we delete a DeviceClass we also delete its devices
        #     and child device classes and their devices, so audit them all.
        if isinstance(node, DeviceClass):
            childBrains = ICatalogTool(node).search((
                'Products.ZenModel.DeviceClass.DeviceClass',
                'Products.ZenModel.Device.Device',
            ))
            for child in childBrains:
                audit(['UI', getDisplayType(child), 'Delete'], child.getPath())
        else:
            audit(['UI', getDisplayType(node), 'Delete'], node)

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
        display_type = getDisplayType(facade._getObject(organizerUid))
        audit(['UI', display_type, 'Move'], organizerUid, to=targetUid)
        data = facade.moveOrganizer(targetUid, organizerUid)
        return DirectResponse.succeed(data=Zuul.marshal(data))

    def _getFacade(self):
        """
        Abstract method for child classes to use to get their facade
        """
        raise NotImplementedError("You must implement the _getFacade method")

    def asyncGetTree(self, id=None, additionalKeys=()):
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
        showEventSeverityIcons = self.context.dmd.UserInterfaceSettings.getInterfaceSettings().get('showEventSeverityIcons')
        facade = self._getFacade()
        currentNode = facade.getTree(id)
        # we want every tree property except the "children" one
        keys = ('id', 'path', 'uid', 'iconCls', 'text', 'hidden', 'leaf') + additionalKeys

        # load the severities in one request
        childNodes = list(currentNode.children)
        if showEventSeverityIcons:
            uuids = [n.uuid for n in childNodes if n.uuid]
            zep = Zuul.getFacade('zep', self.context.dmd)

            if uuids:
                severities = zep.getWorstSeverity(uuids)
                for child in childNodes:
                    if child.uuid:
                        child.setSeverity(zep.getSeverityName(severities.get(child.uuid, 0)).lower())

        children = []
        # explicitly marshall the children
        for child in childNodes:
            childData = Marshaller(child).marshal(keys)
            children.append(childData)
        children.sort(key=lambda e: (e['leaf'], e['uid'].lower()))
        obj = currentNode._object._unrestrictedGetObject()

        # check to see if we are asking for the root
        primaryId = obj.getDmdRoot(obj.dmdRootName).getPrimaryId()
        if id == primaryId:
            root = Marshaller(currentNode).marshal(keys)
            root['children'] = children
            return [root]
        return children

    def objectExists(self, uid):
        """
        @rtype:  DirectResponse
        @return:
            - Properties:
                - B{exists} - Returns true if we can find the object specified by the uid

        """
        from Products.Zuul.facades import ObjectNotFoundException
        facade = self._getFacade()
        try:
            facade._getObject(uid)
            exists = True
        except ObjectNotFoundException:
            exists = False
        return DirectResponse(success=True, exists=exists)

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
