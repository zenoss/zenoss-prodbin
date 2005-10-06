#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################


__doc__="""Organizer

$Id: DeviceOrganizer.py,v 1.6 2004/04/22 19:08:47 edahl Exp $"""

__version__ = "$Revision: 1.6 $"[11:-2]

from Globals import InitializeClass
from Acquisition import aq_parent
from AccessControl import ClassSecurityInfo

from Products.ZenUtils.Utils import travAndColl
from Products.ZenUtils.Exceptions import ZenPathError
from Products.ZenModel.ZenModelRM import ZenModelRM
        
class Organizer(ZenModelRM):
    """
    OrganizerBase class is base for all hierarchical organization classes.
    It allows Organizers to be addressed and created with file system like
    paths like /Devices/Servers.  Organizers have a containment relation
    called children.  Subclasses must define the attribute:

    dmdRootName - root in the dmd database for this organizer
    """

    dmdSubRel = "children"

    _properties = (
                    {'id':'description', 'type':'string', 'mode':'w'},
                   ) 
    
    security = ClassSecurityInfo()
    security.declareObjectProtected("View")

    def __init__(self, id, description = ''):
        ZenModelRM.__init__(self, id)
        self.description = description
   

    security.declareProtected('Add DMD Objects', 'manage_addOrganizer')
    def manage_addOrganizer(self, newPath, REQUEST=None):
        """add a device group to the database"""
        if newPath.startswith("/"):
            self.createOrganizer(newPath)
        else:
            org = self.__class__(newPath)
            self.children.addRelation(org)
        if REQUEST: return self.callZenScreen(REQUEST)
            

    security.declareProtected('Delete objects', 'manage_deleteOrganizer')
    def manage_deleteOrganizer(self, orgname, REQUEST=None):
        """Delete an Organizer from its parent name is relative to parent"""
        self.children._delObject(orgname)
        if REQUEST: return self.callZenScreen(REQUEST)


    security.declareProtected('Delete objects', 'manage_deleteOrganizers')
    def manage_deleteOrganizers(self, organizerPaths, REQUEST=None):
        """add a device group to the database"""
        orgroot = self.getDmdRoot(self.dmdRootName)
        for organizerName in organizerPaths:
            try:
                organizer = orgroot.getOrganizer(organizerName)
                parent = aq_parent(organizer)
                parent.removeRelation(organizer)
            except ZenPathError:
                pass  # we may have already deleted a sub object
        if REQUEST: return self.callZenScreen(REQUEST)
            

    def createOrganizer(self, path):
        """Create and return and an Organizer from its path."""
        return self.createHierarchyObj(self.getDmdRoot(self.dmdRootName), path,
                            self.__class__, self.dmdSubRel)


    def getOrganizer(self, path):
        """Return and an Organizer from its path."""
        return self.getHierarchyObj(self.getDmdRoot(self.dmdRootName), 
                                    path, self.dmdSubRel)


    def getOrganizerName(self):
        """Return the DMD path of an Organizer without its dmdSubRel names."""
        return self.getPrimaryDmdId(self.dmdRootName, self.dmdSubRel)
   
    # getPathName used by Device in _setRelations when setting a device to many
    getPathName = getOrganizerName


    def getOrganizerNames(self, addblank=False):
        """Return the DMD paths of all Organizers below this instance."""
        groupNames = []
        if self.id != self.dmdRootName:
            groupNames.append(self.getOrganizerName())
        for subgroup in self.children():
            groupNames.extend(subgroup.getOrganizerNames())
        if self.id == self.dmdRootName: 
            if addblank: groupNames.append("")
            groupNames.sort(lambda x,y: cmp(x.lower(), y.lower()))
        return groupNames


    def _getCatalog(self):
        """
        Return the ZCatalog instance for this Organizer. Catelog is found
        using the attribute class_default_catalog.
        """
        catalog = None
        if hasattr(self, self.class_default_catalog):
            catalog = getattr(self, self.class_default_catalog)
        return catalog


    def getSubOrganizers(self):
        """build a list of all organizers below this one"""
        orgs = self.children()
        for child in self.children():
            orgs.extend(child.getSubOrganizers())
        return orgs


InitializeClass(Organizer)

