#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""RelationshipAlias


RelationshipAlias is an object that points to a real object from a relationship
If it is called it returns the related object.  A ToManyRelationship
manages a group of RelationshipAliases, a ToOneRelationship is a type
of RelationshipAlias.

$Id: RelationshipAlias.py,v 1.3 2002/05/31 17:40:15 edahl Exp $"""

__version__ = "$Revision: 1.3 $"[11:-2]

from Globals import Persistent
from Globals import InitializeClass
from Globals import DTMLFile
from AccessControl.Role import RoleManager
from OFS.SimpleItem import Item
from Acquisition import Implicit
from Acquisition import aq_chain
from AccessControl import ClassSecurityInfo
from App.Dialogs import MessageDialog

from SchemaManager import SchemaError

class RelationshipAlias(Implicit, Persistent, Item):

    meta_type = 'Relationship Alias'
   
    security = ClassSecurityInfo()

    def __init__(self, id, obj):
        self.id = id
        self.title = obj.title
        self.obj = obj 


    def __call__(self):
        """return the related object when a ToOne relation is called"""
        return self.obj


    def manage_workspace(self, REQUEST):
        """return the workspace of the related object"""
        if self.obj:
            objurl = self.obj.getPrimaryUrlPath()
            raise "Redirect", REQUEST['BASE0']+objurl+'/manage_workspace'
        else:
            return MessageDialog(
                title = "No Relationship Error",
                message = "This relationship does not currently point to an object",
                action = "manage_main")


    def manage_main(self, REQUEST=None):
        """redirect to parent relationship manager"""
        raise "Redirect", self.aq_parent.absolute_url()+'/manage_workspace'

        
