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

from SchemaManager import SchemaError
from RelationshipBase import checkContainer
from RelationshipAlias import RelationshipAlias
from RelTypes import *

def manage_addToOneRelationship(context, id, title = None,
                                    REQUEST = None):
    """ToOneRelationship Factory"""
    r =  ToOneRelationship(id, title)
    try:
        context._setObject(id, r)
    except SchemaError:
        if REQUEST:
            return   MessageDialog(
                title = "Relationship Schema Error",
                message = "There is no Relationship Schema defined for Relationship %s" % id,
                action = "manage_main")
        else:
            raise
    except "InvalidContainer":
        if REQUEST:
            return MessageDialog(
                title = "Relationship Add Error",
                message = "Must add Relationship to RelationshipManager",
                action = "manage_main")
        else:
            raise

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main')


addToOneRelationship = DTMLFile('dtml/addToOneRelationship',globals())


class ToOneRelationship(RelationshipAlias):
    """ToOneRelationship represents a to one Relationship on an object manager"""

    meta_type = 'To One Relationship'
   
    security = ClassSecurityInfo()

    def __init__(self, id, title = None):
        self.id = id
        self.title = title
        self.obj = None
        self._relationType = 0


    def manage_afterAdd(self, item, container):
        """figure out if we have been added to a valid object"""
        checkContainer(container)
        if not self._relationType:
            rs = self.getRelSchema(self.id)
            self._relationType = rs.relationType()


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


    security.declarePrivate('relationType')
    def relationType(self):
        return self._relationType
   

    def _addToOne(self, obj):
        """add a to one side of a relationship"""
        self.obj = obj
        self.title = obj.id
  

    def _removeToOne(self):
        """remove the to one side of a relationship"""
        self.obj = None 
        self.title = None
        self.obj = None

    security.declareProtected('View', 'getRelatedId')
    def getRelatedId(self):
        '''Override getId to return the id of the object,
        not the relationship'''
        if self.obj:
            return self.obj.id
        else:
            return None

    def _getCopy(self, container):
        """create toone copy and if we are the one side of one to many
        we set our side of the relation to point towards the related
        object (we maintain the relationship across the copy)"""
        rel = self.__class__(self.id)
        rel = rel.__of__(container)
        name = self.id
        rs = self.getRelSchema(name)
        rtype = rs.remoteType(name)
        if (rtype == TO_MANY and self.obj and
            self.getPrimaryUrlPath().find(self.obj.getPrimaryUrlPath()) != 0):
            container.addRelation(name, self.obj)
        return rel


    def exportXml(self):
        """return an xml representation of a ToOneRelationship
        <toone id='cricket'>
            /Monitors/Cricket/crk0.srv.hcvlny.cv.net
        </toone>"""
        stag = "<toone id='%s'>" % self.id
        if self.obj:
            value = self.obj.getPrimaryId()
            return "\n".join((stag, value, "</toone>"))
        return "" 
    
    
InitializeClass(ToOneRelationship)
