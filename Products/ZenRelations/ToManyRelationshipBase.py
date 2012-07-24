##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """ToManyRelationshipBase
Base class for 1:n relations
"""
import logging
log = logging.getLogger('zen.ToManyRelationshipBase')

# Base classes for ToManyRelationshipBase
#from PrimaryPathObjectManager import PrimaryPathObjectManager
from RelationshipBase import RelationshipBase
from RelCopySupport import RelCopyContainer

from Globals import DTMLFile
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from App.Management import Tabs

from Products.ZenRelations.Exceptions import zenmarker
from Products.ZenUtils.Utils import unused

class ToManyRelationshipBase(
            RelCopyContainer,
            RelationshipBase
            ):
    """
    Abstract base class for all ToMany relationships.
    """

    manage_options = (
        {
        'action': 'manage_main',
        'help': ('OFSP', 'ObjectManager_Contents.stx'),
        'label': 'Contents'},
    )

    security = ClassSecurityInfo()

    manage_main = DTMLFile('dtml/ToManyRelationshipMain',globals())

    _operation = -1 # if a Relationship's are only deleted

    _count = None

    def setCount(self):
        self._count = len(self._objects)
        # persist the changes if we are on the object graph
        try:
            parent = self.__primary_parent__
            parent._p_changed = True
        except AttributeError:
            log.debug("Unable to persist the count of %s" % self.id)

    def countObjects(self):
        """Return the number of objects in this relationship"""
        if self._count is None:
            self.setCount()
        return self._count


    def findObjectsById(self, partid):
        """Return a list of objects by running find on their id"""
        objects = []
        for id, obj in self.objectItemsAll():
            if id.find(partid) > -1:
                objects.append(obj)
        return objects


    def _delObject(self, id, dp=1, suppress_events=False):
        """Emulate ObjectManager deletetion."""
        unused(dp)
        obj = self._getOb(id, False)
        if not obj:
            log.warning(
            "Tried to delete object id '%s' but didn't find it on %s",
            id, self.getPrimaryId())
            return
        self.removeRelation(obj, suppress_events)
        obj.__primary_parent__ = None


    def _setOb(self, id, obj):
        """don't use attributes in relations"""
        unused(id)
        unused(obj)
        if True:
            raise NotImplementedError


    def _delOb(self, id):
        """don't use attributes in relations"""
        if True:
            raise NotImplementedError


    def _getOb(self, id, default=zenmarker):
        """
        Return object by id if it exists on this relationship.
        If it doesn't exist return default or if default is not set
        raise AttributeError
        """
        unused(default)
        if True:
            raise NotImplementedError


    def manage_workspace(self, REQUEST):
        """if this has been called on us return our workspace
        if not redirect to the workspace of a related object"""
        id = REQUEST['URL'].split('/')[-2]
        if id == self.id:
            Tabs.manage_workspace(self, REQUEST)
        else:
            obj = self._getOb(self, id)
            from zExceptions import Redirect
            raise Redirect( (obj.getPrimaryUrlPath()+'/manage_workspace') )


InitializeClass(ToManyRelationshipBase)
