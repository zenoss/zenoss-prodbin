#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""DeviceGroup

DeviceGroup represents a group of devices

$Id: DeviceGroup.py,v 1.15 2004/04/04 01:51:19 edahl Exp $"""

__version__ = "$Revision: 1.15 $"[11:-2]

from Globals import DTMLFile
from Globals import InitializeClass

from Products.CMFCore import CMFCorePermissions

from Instance import Instance
from DeviceGroupInt import DeviceGroupInt

def manage_addDeviceGroup(context, id, title = None, REQUEST = None):
    """make a DeviceGroup"""
    d = DeviceGroup(id, title)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addDeviceGroup = DTMLFile('dtml/addDeviceGroup',globals())

class DeviceGroup(Instance, DeviceGroupInt):
    """DeviceGroup object"""
    portal_type = meta_type = 'DeviceGroup'
    _properties = (
                    {'id':'description', 'type':'text', 'mode':'w'},
                   ) 

    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'id'             : 'DeviceGroup',
            'meta_type'      : 'DeviceGroup',
            'description'    : """Arbitrary device grouping class""",
            'icon'           : 'DeviceGroup_icon.gif',
            'product'        : 'Confmon',
            'factory'        : 'manage_addDeviceGroup',
            'immediate_view' : 'viewGroupOverview',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewGroupOverview'
                , 'permissions'   : (
                  CMFCorePermissions.View, )
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (
                  CMFCorePermissions.View, )
                },
                { 'id'            : 'view'
                , 'name'          : 'View'
                , 'action'        : 'viewItem'
                , 'permissions'   : (
                  CMFCorePermissions.View, )
                , 'visible'       : 0
                },
            )
          },
        )
    
    def __init__(self, id, title = None, description = ''):
        Instance.__init__(self, id, title)
        self.description = description


InitializeClass(DeviceGroup)
