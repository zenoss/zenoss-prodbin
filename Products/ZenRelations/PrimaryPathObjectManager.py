#################################################################
#
#   Copyright (c) 2005 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""PrimaryPathObjectManager

$Id: RelationshipBase.py,v 1.26 2003/10/03 16:16:01 edahl Exp $"""

__version__ = "$Revision: 1.26 $"[11:-2]

# base classes for PrimaryPathObjectManager
from RelCopySupport import RelCopyContainer
from OFS.Traversable import Traversable
from Acquisition import Implicit, aq_base
from OFS.ObjectManager import ObjectManager
from AccessControl.Role import RoleManager
import App.Undo

from ZItem import ZItem


from Products.ZenUtils.Utils import getObjByPath

from Products.BTreeFolder2.BTreeFolder2 import BTreeFolder2



class PrimaryPathManager(ZItem, Implicit, RoleManager):

    def getPrimaryPath(self, fromNode=None):
        """
        Return the primary path of this object by following __primary_parent__
        """
        ppath = []
        obj = aq_base(self)
        while True:
            ppath.append(obj.id)
            parent = getattr(obj, "__primary_parent__", None)
            if parent is None: break
            obj = parent
        ppath.reverse()
        basepath = getattr(obj, "zPrimaryBasePath", [])
        for i in range(len(basepath)-1,-1,-1): ppath.insert(0,basepath[i])
        try:
            idx = ppath.index(fromNode)
            ppath = ppath[idx+1:]
        except ValueError: pass
        return tuple(ppath)

    
    def getPrimaryId(self, fromNode=None):
        """Return the primary path in the form /zport/dmd/xyz"""
        pid = "/".join(self.getPrimaryPath(fromNode))
        if fromNode: pid = "/" + pid
        return pid


    def getPrimaryUrlPath(self, full=False):
        """Return the primary path as an absolute url"""
        objaq = self.primaryAq()
        if full: return objaq.absolute_url()
        return objaq.absolute_url_path()
        


    def primaryAq(self):
        """Return self with is acquisition path set to primary path"""
        app = self.getPhysicalRoot()
        return getObjByPath(app, self.getPrimaryPath())
       

    def getPrimaryParent(self):
        """Return our parent object by our primary path"""
        return self.__primary_parent__.primaryAq()



class PrimaryPathObjectManager(
            RelCopyContainer,
            ObjectManager, 
            PrimaryPathManager, 
            App.Undo.UndoSupport,
            ):
    """
    PrimaryPathObjectManager with basic Zope persistent classes.
    """
    manage_options = (ObjectManager.manage_options +
                      RoleManager.manage_options +
                      ZItem.manage_options)

    def _noticeChange(self):
        # the object may not be hooked in to have acquisition yet
        try:
            self.notifyObjectChange(self)
        except AttributeError:
            pass

    def _setObject(self, id, obj, roles=None, user=None, set_owner=1):
        """Track __primary_parent__ when we are set into an object"""
        self._noticeChange()
        obj.__primary_parent__ = aq_base(self)
        return ObjectManager._setObject(self, id, obj, roles, user, set_owner)


    def _delObject(self, id, dp=1):
        """When deleted clear __primary_parent__."""
        self._noticeChange()
        obj = self._getOb(id)
        ObjectManager._delObject(self, id, dp)
        obj.__primary_parent__ = None


class PrimaryPathBTreeFolder2(BTreeFolder2):
    """
    BTreeFolder2 PrimaryPathObjectManager.
    """
    def _setObject(self, id, obj, roles=None, user=None, set_owner=1):
        """Track __primary_parent__ when we are set into an object"""
        self._noticeChange()
        obj.__primary_parent__ = aq_base(self)
        return ObjectManager._setObject(self, id, obj, roles, user, set_owner)


    def _delObject(self, id, dp=1):
        """When deleted clear __primary_parent__."""
        self._noticeChange()
        obj = self._getOb(id)
        ObjectManager._delObject(self, id, dp)
        obj.__primary_parent__ = None
