#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""ToOneRelationship

ToOneRelationship is a class used on a RelationshipManager
to give it toOne management Functions.

$Id: ToOneRelationship.py,v 1.23 2003/10/02 20:48:22 edahl Exp $"""

__version__ = "$Revision: 1.23 $"[11:-2]

import copy

from Globals import InitializeClass
from Globals import DTMLFile
from AccessControl import ClassSecurityInfo
from App.Dialogs import MessageDialog
from Acquisition import aq_base, aq_parent

from SchemaManager import SchemaError
from RelationshipBase import RelationshipBase
from RelTypes import *

from Products.ZenRelations.Exceptions import InvalidContainer

def manage_addToOneRelationship(context, id, REQUEST = None):
                                    
    """ToOneRelationship Factory"""
    r =  ToOneRelationship(id)
    try:
        if not getattr(aq_base(context), "getRelSchema", False):
            raise InvalidContainer, \
                "Container %s is not a RelatioshipManager" % context.id
        context._setObject(id, r)
    except SchemaError:
        if REQUEST:
            return   MessageDialog(
                title = "Relationship Schema Error",
                message = "There is no Relationship Schema defined for "
                          "Relationship %s" % id,
                action = "manage_main")
        raise
    except InvalidContainer:
        if REQUEST:
            return MessageDialog(
                title = "Relationship Add Error",
                message = "Must add Relationship to RelationshipManager",
                action = "manage_main")
        raise
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main')


addToOneRelationship = DTMLFile('dtml/addToOneRelationship',globals())


class ToOneRelationship(RelationshipBase):
    """ToOneRelationship represents a to one Relationship 
    on a RelationshipManager"""

    meta_type = 'To One Relationship'
   
    security = ClassSecurityInfo()


    def __init__(self, id):
        self.id = id
        self.obj = None

    
    def __call__(self):
        """return the related object when a ToOne relation is called"""
        return self.obj


    def addRelation(self, obj):
        """form a relation with obj"""
        name = self.id
        rs = self.getRelSchema(name)
        self._checkSchema(name, rs, obj)
        self._add(obj)
        obj = obj.__of__(self)
        obj._add(rs.remoteAtt(name), aq_parent(self))
 

    def removeRelation(self, obj=None):
        """remove the relationship with the current object if there is one."""
        if obj == None or self.obj == obj:
            self._remoteRemove(obj)
            self._remove(obj)
        
        
    def _add(self, obj):
        """add a to one side of a relationship
        if a relationship already exists clear it"""
        self._remoteRemove()
        self.obj = aq_base(obj)


    def _remove(self,obj=None):
        """remove the to one side of a relationship"""
        self.obj = None 


    def _remoteRemove(self, obj=None):
        """clear the remote side of this relationship"""
        if self.obj:
            rs = self.getRelSchema(self.id)
            self.obj._remove(rs.remoteAtt(self.id), aq_parent(self))


    def hasobject(self, obj):
        """does this relation point to the object passed"""
        return self.obj == obj


    security.declareProtected('View', 'getPrimaryLink')
    def getPrimaryLink(self, target='rightFrame'):
        """get the link tag of a related object"""
        link = None
        if self.obj:
            link = "<a href='"+ self.obj.getPrimaryUrlPath()+"'"
            if target:
                link += " target='"+ target+ "'"
            link += " >"+ self.obj.id+ "</a>"
        return link


    def _getCopy(self, container):
        """create toone copy and if we are the one side of one to many
        we set our side of the relation to point towards the related
        object (we maintain the relationship across the copy)"""
        rel = self.__class__(self.id)
        rel = rel.__of__(container)
        name = self.id
        rs = self.getRelSchema(name)
        rtype = rs.remoteType(name)
        if (rtype == TO_MANY and self.obj):
            rel.addRelation(self.obj)
        return rel


    def manage_beforeDelete(self, item, container):
        """if relationship is being deleted remove the remote side"""
        self._remoteRemove()


    def manage_workspace(self, REQUEST):
        """ZMI function to return the workspace of the related object"""
        if self.obj:
            objurl = self.obj.getPrimaryUrlPath()
            raise "Redirect", REQUEST['BASE0']+objurl+'/manage_workspace'
        else:
            return MessageDialog(
                title = "No Relationship Error",
                message = "This relationship does not currently point" \
                            " to an object",
                action = "manage_main")


    def manage_main(self, REQUEST=None):
        """ZMI function to redirect to parent relationship manager"""
        raise "Redirect", self.aq_parent.absolute_url()+'/manage_workspace'

        
    def checkRelation(self, repair=False, log=None):
        """confirm that this relation is still bidirectional
        if clean is set remove any bad relations"""
        if not self.obj: return
        rs = self.getRelSchema(self.id)
        ratt = rs.remoteAtt(self.id)
        rrel = getattr(self.obj, ratt)
        parent = aq_parent(self)
        if not rrel.hasobject(parent):
            if log: log.critical(
                    "BAD ToOne relation %s from %s to %s" 
                    % (self.id, parent.getPrimaryDmdId(), 
                        self.obj.getPrimaryDmdId()))
            if repair: 
                goodobj = self.getDmdObj(self.obj.getPrimaryDmdId()) 
                if goodobj:
                    if log: log.warn("RECONNECTING relation %s to obj %s" %
                        (self.id, goodobj.getPrimaryDmdId()))
                    self._remove()
                    parent.addRelation(self.id, goodobj)
                else:
                    if log: log.warn(
                        "CLEARING relation %s to obj %s" %
                        (self.id, self.obj.getPrimaryDmdId()))
                    self._remove()



InitializeClass(ToOneRelationship)
