#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""RelationshipBase

RelationshipBase is the base class for RelationshipManager
and ToManyRelationship.

$Id: RelationshipBase.py,v 1.26 2003/10/03 16:16:01 edahl Exp $"""

__version__ = "$Revision: 1.26 $"[11:-2]

import urllib

from Globals import Persistent
from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl.Role import RoleManager
from OFS.SimpleItem import Item
from OFS.ObjectManager import ObjectManager
from Acquisition import Implicit, aq_base
from AccessControl import ClassSecurityInfo
from App.Dialogs import MessageDialog

from OFS.CopySupport import CopyError

from Products.ConfUtils.Utils import checkClass, getObjByPath

from RelCopySupport import RelCopyContainer
from SchemaManager import SchemaError

def checkZClass(zbases, className):
    """walk zclass for looking for className"""
    retval = 0
    for zb in zbases:
        if hasattr(zb, '_zclass_'):
            retval = checkClass(zb._zclass_, className)
            if retval: break
    return retval


def checkContainer(container):
    """check to see if we are being added to a valid conatiner"""
    from RelationshipManager import RelationshipManager
    from RelationshipBase import checkZClass
    # isinstance seems to be broken in the zope context
    #if isinstance(container, RelationshipManager): return
    if checkClass(container.__class__, "RelationshipManager"): return
    meta_type = getattr(container, 'meta_type')
    if callable(meta_type):
        meta_type = container.meta_type()
    if (meta_type == 'Z Class' and   
        checkZClass(container.aq_acquire('_zbases'), "RelationshipManager")):
        return
    get_transaction().abort()        
    raise ("InvalidContainer", 
        "Relationship must be added to an instance of RelationshipManager")



class RelationshipBase(ObjectManager, RelCopyContainer, Implicit, 
                        Persistent, RoleManager, Item):
    """RelationshipBase is a base class for RelationhshipManager
    and ToManyRelationship.  It defines the basic relationship
    interface as well as some schema checking and access functions"""
    
    manage_main=DTMLFile('dtml/RelationshipManagerMain', globals())
    
    manage_options = (ObjectManager.manage_options
                    +RoleManager.manage_options
                    +Item.manage_options)

    security = ClassSecurityInfo()
    security.setDefaultAccess('allow')
 

    def _verifyObjectPaste(self, object, validate_src=1):
        "check to see if this object is allowed to be pasted into this path"
        pathres = getattr(object, 'relationshipManagerPathRestriction', None)
        if (pathres and '/'.join(self.getPhysicalPath()).find(pathres) == -1):
            raise CopyError, MessageDialog(
                  title='Not Supported',
                  message='The object <EM>%s</EM> can not be pasted into' \
                          ' the path <EM>%s</EM>' % (object.id, 
                                            '/'.join(self.getPhysicalPath())),
                  action='manage_main')
        else:
            ObjectManager._verifyObjectPaste(self,object,validate_src)


    def _verifyObjectLink(self, object, validate_src=1):
        ObjectManager._verifyObjectPaste(self,object,validate_src)
        

    def _renameObject(self, id, new_id):
        """Rename a particular sub-object from program code
        used because normal rename requires user permission info"""
        try: self._checkId(new_id)
        except: raise CopyError, 'Invalid id %s' % new_id 
        ob=self._getOb(id)
        if not ob.cb_isMoveable():
            raise CopyError, eNotSupported % id            
        try:    ob._notifyOfCopyTo(self, op=1)
        except: raise CopyError, "Invalid container for object %s" % id
        self._delObject(id)
        ob = aq_base(ob)
        ob._setId(new_id)
        self._setObject(new_id, ob, set_owner=0)
   

    def setPrimaryPath(self, force=0):
        """set the physical path this is the 'normal' zope path to the
        object (ie not by navigating down a relationship.  We use this
        to navigate to the object from a related object"""
        if (force or 
            not self.getPrimaryPath() or
            not self.checkPath(self.getPhysicalRoot(), 
                                self.getPrimaryPath()[1:])):

            self.primaryPath = self.getPhysicalPath()
            return 1
        else:
            return 0
       

    def getPrimaryPath(self):
        """get primary physical path"""
        return self.primaryPath

    
    def getPrimaryId(self):
        """get the full primary id of this object in the form /zport/dmd/xyz"""
        return '/'.join(self.getPrimaryPath())


    def getPrimaryUrlPath(self):
        """get the physicalpath as a url"""
        return urllib.quote(self.getPrimaryId())


    def checkPath(self, object, path):
        """figure out if we need to rebuild the physical path (we moved or are new)"""
        return getObjByPath(object, path)


    def aq_primary(self):
        """return this object with is acquisition path set to primary path"""
        return getObjByPath(self.getPhysicalRoot(), self.getPrimaryPath()[1:])
    
    def primaryAq(self):
        """return this object with is acquisition path set to primary path"""
        return self.aq_primary()
       

    def getParent(self):
        """return our parent container by walking our primary path"""
        app = self.getPhysicalRoot()
        path = self.getPrimaryPath()[1:-1]
        return getObjByPath(app, path)     

        

    def getClass(self):
        """return the class of the local end of the relationship

        if we are a ToMany end of a relationship we set this to
        our parent class type"""
        return self.__class__


    def _checkSchema(self, name, rel, obj):
        """check the relationship object aginst the schema"""
        try:
            if (obj.meta_type != rel.remoteClass(name) and 
                not checkClass(obj.getClass(), rel.remoteClass(name))):
                mess = ("On relation " + name + " neither object class " 
                                    + obj.getClass().__name__ 
                                    + " nor meta_type " + obj.meta_type 
                                    + "  match remote schema type "
                                    + rel.remoteClass(name))
                raise SchemaError, mess
        except AttributeError:
            raise SchemaError, "Linked objects must be an instance of RelationshipManager"
          

InitializeClass(RelationshipBase)
