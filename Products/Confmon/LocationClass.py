#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""LocationClass

The device classification class.  default identifiers, screens,
and data collectors live here.

$Id: LocationClass.py,v 1.12 2004/04/22 02:14:12 edahl Exp $"""

__version__ = "$Revision: 1.12 $"[11:-2]

from Globals import InitializeClass
from OFS.Folder import Folder
from Globals import DTMLFile

from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Classification import Classification

def manage_addLocationClass(context, id, title = None, REQUEST = None):
    """make a device class"""
    lc = LocationClass(id, title)
    context._setObject(id, lc)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addLocationClass = DTMLFile('dtml/addLocationClass',globals())

class LocationClass(Classification, Folder):

    portal_type = meta_type = "LocationClass"
    manage_main = Folder.manage_main
    manage_options = Folder.manage_options

    factory_type_information = ( 
        { 
            'id'             : 'LocationClass',
            'meta_type'      : 'LocationClass',
            'description'    : """LocationClass class""",
            'icon'           : 'LocationClass_icon.gif',
            'product'        : 'Confmon',
            'factory'        : 'manage_addLocationClass',
            'immediate_view' : 'viewLocationClassOverview',
            'actions'        :
            ( 
                { 'id'            : 'view'
                , 'name'          : 'View'
                , 'action'        : 'viewLocationClassOverview'
                , 'permissions'   : ("View", )
                , 'visible'       : 0
                },
            )
          },
        )


    def getRackLocation(self, path):
        """get or create a rack in a location path.  
        rack name is last element of path"""
        from Products.ZenModel.Location import manage_addLocation
        from Products.ZenModel.Rack import manage_addRack
        locpath = self.zenpathsplit(path)
        if locpath[0] != "Locations": locpath.insert(0,"Locations")
        try:
            rackname = locpath[-1]
            idx = rackname.index("-")
            rackslot = rackname[:idx]
            self.rackslot = int(rackslot)
            locpath[-1] = rackname[idx+1:]
        except ValueError:
            pass
        locName = self.zenpathjoin(locpath)
        locobj =  self.getHierarchyObj(self.getDmd(), locName,
                                manage_addLocation,
                                lastfactory=manage_addRack,
                                relpath='sublocations', 
                                lastrelpath='racks')
        return locobj


    def getLocation(self, path):
        """get or create a location based on a path"""
        from Products.ZenModel.Location import manage_addLocation
        path = self.zenpathsplit(path)
        if path[0] != "Locations": path.insert(0,"Locations")
        name = self.zenpathjoin(path)
        locobj =  self.getHierarchyObj(self.getDmd(), name,
                                manage_addLocation,
                                relpath='sublocations')
        return locobj    


    def getLocationNames(self):
        """return a list of all the location paths"""
        locnames = ["",]
        for location in self.objectValues():
            locnames.extend(location.getLocationNames())
        return locnames
       

InitializeClass(LocationClass)
