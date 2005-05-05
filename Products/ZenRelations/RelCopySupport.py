##############################################################################
#
# Copyright (c) 2002 Confmon Corporation. All Rights Reserved.
# 
##############################################################################

"""MultiCopySupport

MultiCopySupport over rides manage_pasteObjects in CopySupport to handle
cut/past for a MultiItem.  Semantics of cut/paste are to remove time from
current container and put it in new container but other container mappings
remain.

$Id: RelCopySupport.py,v 1.15 2004/04/13 22:02:18 edahl Exp $"""

__version__ = '$Revision: 1.15 $'

from OFS import Moniker
from OFS.CopySupport import CopyContainer
from OFS.CopySupport import CopySource
from OFS.CopySupport import _cb_encode, _cb_decode
from OFS.CopySupport import CopyError
from OFS.CopySupport import eInvalid, eNotFound
from App.Dialogs import MessageDialog

from Products.ZenRelations.Exceptions import *
from RelTypes import *

class RelCopyContainer(CopyContainer):

    def manage_linkObjects(self, ids = None, cb_copy_data=None, REQUEST=None):
        """link objects to relationship"""
        try:
            relName = self._getRelName(ids)
        except "RelNameError":
           return MessageDialog(
            title = "Relationship Link Error",
            message = "You can only link to one relationship at a time",
            action = "manage_main")     
        
        oblist = self._getSourceObjects(cb_copy_data, REQUEST)
        try:
            for obj in oblist:
                self.manage_addRelation(relName, obj)
        except SchemaError, e:
            return MessageDialog(
                title = "Relationship Add Error",
                message = e.args[0],
                action = "manage_main")
        if REQUEST:
            return self.manage_main(self, REQUEST)


    def manage_unlinkObjects(self, ids = None, cb_copy_data=None, REQUEST=None):
        """unlink objects from relationship"""
        try:
            relName = self._getRelName(ids)
        except "RelNameError":
           return MessageDialog(
            title = "Relationship Remove Error",
            message = "You can only link to one relationship at a time",
            action = "manage_main")     
        self.manage_removeRelation(relName)
        if REQUEST:
            return self.manage_main(self, REQUEST)


    def _getRelName(self, ids):
        """get our relationship name from the UI

        if there is more than one id defined raise because only one
        target relationship can be defined.  If no ids are defined
        we assume (bad??) that this is a toManyRelationship and get
        its id as the relName"""
        relName = None
        if type(ids) is type(''): ids=[ids]
        if not ids:
            relName = self.getId()    
        elif len(ids) > 1: 
            raise "RelNameError", "You can only link to one relationship!"
        else:
            relName = ids[0] 
        return relName
   

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
            self._verifyObjectLink(ob) 
            oblist.append(ob)
        return oblist

