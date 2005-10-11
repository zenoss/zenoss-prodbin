##############################################################################
#
# Copyright (c) 2002 Zentinel Systems, Inc. All Rights Reserved.
# 
##############################################################################

"""MultiCopySupport

MultiCopySupport over rides manage_pasteObjects in CopySupport to handle
cut/past for a MultiItem.  Semantics of cut/paste are to remove time from
current container and put it in new container but other container mappings
remain.

$Id: RelCopySupport.py,v 1.15 2004/04/13 22:02:18 edahl Exp $"""

__version__ = '$Revision: 1.15 $'

import types

from Acquisition import aq_base
from AccessControl import getSecurityManager

from OFS import Moniker
from OFS.CopySupport import CopyContainer, CopyError, \
                            _cb_decode, eInvalid, eNotFound
from App.Dialogs import MessageDialog

from Products.ZenRelations.Exceptions import *

class RelCopyContainer(CopyContainer):

    def manage_renameObject(self, id, new_id, REQUEST=None):
        """Rename a particular sub-object"""
        try: self._checkId(new_id)
        except: raise CopyError, MessageDialog(
                      title='Invalid Id',
                      message=sys.exc_info()[1],
                      action ='manage_main')
        ob=self._getOb(id)
        if ob.wl_isLocked():
            raise ResourceLockedError(
                    'Object "%s" is locked via WebDAV' % ob.getId())
        if not ob.cb_isMoveable():
            raise CopyError, eNotSupported % escape(id)
        self._verifyObjectPaste(ob)
        try:    ob._notifyOfCopyTo(self, op=2) # -EAD add rename to semantics
        except: raise CopyError, MessageDialog(
                      title='Rename Error',
                      message=sys.exc_info()[1],
                      action ='manage_main')
        self._delObject(id)
        ob = aq_base(ob)
        ob._setId(new_id)

        # Note - because a rename always keeps the same context, we
        # can just leave the ownership info unchanged.
        self._setObject(new_id, ob, set_owner=0)
        ob = self._getOb(new_id)
        ob._postCopy(self, op=1)

        if REQUEST is not None:
            return self.manage_main(self, REQUEST, update_menu=1)
        return None
    
    
    def manage_linkObjects(self, ids = None, cb_copy_data=None, REQUEST=None):
        """link objects to relationship"""
        try:
            relName = self._getRelName(ids)
            oblist = self._getSourceObjects(cb_copy_data, REQUEST)
            for obj in oblist:
                self.manage_addRelation(relName, obj)
        except ZenRelationsError, e:
            if REQUEST: return MessageDialog(title = "Relationship Link Error",
                                message = str(e), action = "manage_main")     
            else: raise
        if REQUEST: return self.manage_main(self, REQUEST)
            


    def manage_unlinkObjects(self, ids = None, cb_copy_data=None, REQUEST=None):
        """unlink objects from relationship"""
        try:
            relName = self._getRelName(ids)
            self.manage_removeRelation(relName)
        except ZenRelationsError, e:
            if REQUEST:return MessageDialog(title = "Relationship Unlink Error",
                                message = str(e), action = "manage_main")     
            else: raise
        if REQUEST: return self.manage_main(self, REQUEST)
            
   
    def _verifyObjectPaste(self, object, validate_src=1):
        """
        check to see if this object is allowed to be pasted into this path
        """
        pathres = getattr(object, 'relationshipManagerPathRestriction', None)
        if (pathres and '/'.join(self.getPhysicalPath()).find(pathres) == -1):
            raise CopyError, MessageDialog(title='Not Supported',
                  message='The object <EM>%s</EM> can not be pasted into' \
                          ' the path <EM>%s</EM>' % 
                           (object.id, '/'.join(self.getPhysicalPath())),
                  action='manage_main')
        CopyContainer._verifyObjectPaste(self,object,validate_src)


    def _getRelName(self, ids):
        """
        Return our relationship name from the UI.
        If there is more than one id defined raise because only one
        target relationship can be defined.  If no ids are defined
        check to see that we are a ToManyRelationship and return self.id.
        """
        if not ids:
            if self.meta_type == "ToManyRelationship": 
                return self.getId()
            else:
                raise ZenRelationsError("No relation name defined")
        if type(ids) == types.StringType: return ids
        if len(ids) > 1: 
            raise ZenRelationsError("You can only link to one relationship!")
        return ids[0] 
   
    
    def _verifyObjectLink(self):
        """
        When linking check that the user has "Copy or Move" permission
        on the relation.  Can't use _verifyObjectPaste because there
        is an empty all_meta_types on ToManyRelations which causes it
        to falsely fail.
        """
        if not getSecurityManager().checkPermission('Copy or Move', self):
            message = ('You do not possess the "Copy or Move" permission in '
                'the context of the container into which you are '
                'pasting, thus you are not able to perform '
                'this operation.')
            raise CopyError, MessageDialog(title = 'Insufficient Privileges',
                                message = message, action = 'manage_main')
                



    def _getSourceObjects(self, cb_copy_data, REQUEST):
        """get the source objects to link"""
        cp=None
        if cb_copy_data is not None:
            cp=cb_copy_data
        else:
            if REQUEST and REQUEST.has_key('__cp'):
                cp=REQUEST['__cp']
        if cp is None:
            raise CopyError, eNoData
        
        try:    cp=_cb_decode(cp)
        except: raise CopyError, eInvalid

        oblist=[]
        op=cp[0]
        app = self.getPhysicalRoot()

        for mdata in cp[1]:
            m = Moniker.loadMoniker(mdata)
            try: ob = m.bind(app)
            except: raise CopyError, eNotFound
            self._verifyObjectLink() 
            oblist.append(ob)
        return oblist


