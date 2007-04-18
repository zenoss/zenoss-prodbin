#################################################################
#
#   Copyright (c) 2005 Zenoss, Inc. All rights reserved.
#
#################################################################


__doc__="""Organizer

$Id: DeviceOrganizer.py,v 1.6 2004/04/22 19:08:47 edahl Exp $"""

__version__ = "$Revision: 1.6 $"[11:-2]

from Globals import InitializeClass
from Acquisition import aq_parent
from AccessControl import ClassSecurityInfo

from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.Utils import travAndColl
from Products.ZenUtils.Exceptions import ZenPathError

from EventView import EventView
from ZenModelRM import ZenModelRM
from ZenPackable import ZenPackable
        
class Organizer(ZenModelRM, EventView):
    """
    OrganizerBase class is base for all hierarchical organization classes.
    It allows Organizers to be addressed and created with file system like
    paths like /Devices/Servers.  Organizers have a containment relation
    called children.  Subclasses must define the attribute:

    dmdRootName - root in the dmd database for this organizer
    """

    _properties = (
                    {'id':'description', 'type':'string', 'mode':'w'},
                   )

    _relations = ZenModelRM._relations
 
    security = ClassSecurityInfo()
    security.declareObjectProtected("View")

    def __init__(self, id, description = ''):
        ZenModelRM.__init__(self, id)
        self.description = description

    def childMoveTargets(self):
        """see IDeviceManager"""
        myname = self.getOrganizerName()
        return filter(lambda x: x != myname, 
                    self.getDmdRoot(self.dmdRootName).getOrganizerNames())


    def getChildMoveTarget(self, moveTargetName): 
        """see IDeviceManager"""
        return self.getDmdRoot(self.dmdRootName).getOrganizer(moveTargetName)

    
    def children(self, sort=False):
        """Return children of our organizer who have same type as parent."""
        kids = self.objectValues(spec=self.meta_type)
        if sort: kids.sort(lambda x,y: cmp(x.primarySortKey(), 
                                           y.primarySortKey()))
        return kids


    def childIds(self):
        """Return Ids of children within our organizer."""
        return self.objectIds(spec=self.meta_type)


    def countChildren(self):
        """Return a count of all our contained children."""
        count = len(self.objectIds(spec=self.meta_type))
        for child in self.children():
            count += child.countChildren()
        return count
        

    security.declareProtected('Add DMD Objects', 'manage_addOrganizer')
    def manage_addOrganizer(self, newPath, REQUEST=None):
        """add a device group to the database"""
        if not newPath: return self.callZenScreen(REQUEST)
        if newPath.startswith("/"):
            self.createOrganizer(newPath)
        else:
            org = self.__class__(newPath)
            self._setObject(org.id, org)
        if REQUEST: return self.callZenScreen(REQUEST)
            

    security.declareProtected('Delete objects', 'manage_deleteOrganizer')
    def manage_deleteOrganizer(self, orgname, REQUEST=None):
        """Delete an Organizer from its parent name is relative to parent"""
        if orgname.startswith("/"):
            try:
                orgroot = self.getDmdRoot(self.dmdRootName)
                organizer = orgroot.getOrganizer(orgname)
                parent = aq_parent(organizer)
                parent._delObject(organizer.getId())
            except KeyError:
                pass  # we may have already deleted a sub object
        else:
            self._delObject(orgname)
        if REQUEST: return self.callZenScreen(REQUEST)


    security.declareProtected('Delete objects', 'manage_deleteOrganizers')
    def manage_deleteOrganizers(self, organizerPaths=None, REQUEST=None):
        """Delete a list of Organizers from the database using their ids.
        """
        if not organizerPaths: return self.callZenScreen(REQUEST)
        for organizerName in organizerPaths:
            self.manage_deleteOrganizer(organizerName)
        if REQUEST: return self.callZenScreen(REQUEST)
            
    
    def deviceMoveTargets(self):
        """Return list of all organizers excluding our self."""
        return filter(lambda x: x != self.getOrganizerName(),
            self.getDmdRoot(self.dmdRootName).getOrganizerNames())

   
    def moveOrganizer(self, moveTarget, organizerPaths=None, REQUEST=None):
        """Move organizer to moveTarget."""
        if not moveTarget or not organizerPaths: return self()
        target = self.getDmdRoot(self.dmdRootName).getOrganizer(moveTarget)
        movedStuff = False
        for organizerName in organizerPaths:
            if moveTarget.find(organizerName) > -1: continue
            obj = self._getOb(organizerName)
            obj._operation = 1 #move object
            self._delObject(organizerName)
            target._setObject(organizerName, obj)
            movedStuff = True
        if REQUEST and movedStuff: return target.callZenScreen(REQUEST)
        
    
    def createOrganizer(self, path):
        """Create and return and an Organizer from its path."""
        return self.createHierarchyObj(self.getDmdRoot(self.dmdRootName), 
                                           path,self.__class__)


    def getOrganizer(self, path):
        """Return and an Organizer from its path."""
        if path.startswith("/"): path = path[1:]
        return self.getDmdRoot(self.dmdRootName).getObjByPath(path) 


    def getOrganizerName(self):
        """Return the DMD path of an Organizer without its dmdSubRel names."""
        return self.getPrimaryDmdId(self.dmdRootName)
    getDmdKey = getOrganizerName


    def getOrganizerNames(self, addblank=False):
        """Return the DMD paths of all Organizers below this instance."""
        groupNames = []
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
        using the attribute default_catalog.
        """
        catalog = None
        if hasattr(self, self.default_catalog):
            catalog = getattr(self, self.default_catalog)
        return catalog


    def getSubOrganizers(self):
        """build a list of all organizers below this one"""
        orgs = self.children()
        for child in self.children():
            orgs.extend(child.getSubOrganizers())
        return orgs


    def exportXmlHook(self, ofile, ignorerels):
        """Add export of our child objects.
        """
        map(lambda o: o.exportXml(ofile, ignorerels), self.children())


InitializeClass(Organizer)

