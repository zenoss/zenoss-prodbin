#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""DeviceGroupClass

The device classification class.  default identifiers, screens,
and data collectors live here.

$Id: DeviceGroupClass.py,v 1.13 2004/04/09 00:34:39 edahl Exp $"""

__version__ = "$Revision: 1.13 $"[11:-2]

from Globals import InitializeClass
from OFS.Folder import Folder
from Globals import DTMLFile

from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Classification import Classification

def manage_addDeviceGroupClass(context, id, title = None, REQUEST = None):
    """make a device class"""
    gc = DeviceGroupClass(id, title)
    context._setObject(id, gc)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addDeviceGroupClass = DTMLFile('dtml/addDeviceGroupClass',globals())

class DeviceGroupClass(Classification, Folder):
    portal_type = meta_type = "DeviceGroupClass"
    manage_main = Folder.manage_main
    manage_options = Folder.manage_options
  

    factory_type_information = ( 
        { 
            'id'             : 'DeviceGroupClass',
            'meta_type'      : 'DeviceGroupClass',
            'description'    : """DeviceGroupClass class""",
            'icon'           : 'DeviceGroupClass_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addDeviceGroupClass',
            'immediate_view' : 'viewDeviceGroupClassOverview',
            'actions'        :
            ( 
                { 'id'            : 'view'
                , 'name'          : 'View'
                , 'action'        : 'viewDeviceGroupClassOverview'
                , 'permissions'   : ("View", )
                , 'visible'       : 0
                },
            )
          },
        )
    

    def getDeviceGroup(self, path):
        """get or create a group from a path like /parentgroup/subgroup"""
        from Products.ZenModel.DeviceGroup import manage_addDeviceGroup
        path = self.zenpathsplit(path)
        if path[0] != "Groups": path.insert(0,"Groups")
        name = self.zenpathjoin(path)
        groupObj =  self.getHierarchyObj(self.getDmd(), name,
                                manage_addDeviceGroup,
                                relpath='subgroups')
        return groupObj    


    def getDeviceGroupNames(self):
        """return a list of all the system paths"""
        devnames = ["",]
        for group in self.objectValues():
            devnames.extend(group.getDeviceGroupNames())
        devnames.sort()
        return devnames


InitializeClass(DeviceGroupClass)
