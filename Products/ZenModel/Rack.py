#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""Rack

Rack represents a rack inside a datacenter.

$Id: Rack.py,v 1.15 2003/11/19 03:14:53 edahl Exp $"""

__version__ = "$Revision: 1.15 $"[11:-2]

from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from Globals import InitializeClass
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Products.CMFCore import CMFCorePermissions

from LocationBase import LocationBase

def manage_addRack(context, id, title = None, REQUEST = None):
    """make a Rack"""
    d = Rack(id, title)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addRack = DTMLFile('dtml/addRack',globals())

class Rack(LocationBase):
    """Rack object"""
    portal_type = meta_type = 'Rack'
    view = PageTemplateFile('zpt/viewRackOverview.zpt',globals())
    _properties = (
                    {'id':'description', 'type':'text', 'mode':'w'},
                   ) 

    description = ""

    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'id'             : 'Rack',
            'meta_type'      : 'Rack',
            'description'    : """Class representing racks tha hold devices""",
            'icon'           : 'Rack_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addRack',
            'immediate_view' : 'viewRackOverview',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewRackOverview'
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

    security = ClassSecurityInfo()


    security.declareProtected('View', 'countDevices')
    def countDevices(self):
        """count the number of devices in this rack"""
        return self.devices.countObjects()


InitializeClass(Rack)
