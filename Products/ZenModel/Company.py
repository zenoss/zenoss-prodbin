#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""Company

Company is a base class that represents a vendor of Products.

$Id: Company.py,v 1.11 2004/03/26 23:58:44 edahl Exp $"""

__version__ = "$Revision: 1.11 $"[11:-2]

from Globals import DTMLFile, InitializeClass

from Products.CMFCore import CMFCorePermissions

from Instance import Instance

def manage_addCompany(context, id, REQUEST = None):
    """make a Company"""
    d = Company(id)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addCompany = DTMLFile('dtml/addCompany',globals())

class Company(Instance):
    """Company object"""
    portal_type = meta_type = 'Company'

    _properties = (
                    {'id':'url', 'type':'string', 'mode':'w'},
                    {'id':'supportNumber', 'type':'string', 'mode':'w'},
                    {'id':'address1', 'type':'string', 'mode':'w'},
                    {'id':'address2', 'type':'string', 'mode':'w'},
                    {'id':'city', 'type':'string', 'mode':'w'},
                    {'id':'state', 'type':'string', 'mode':'w'},
                    {'id':'zip', 'type':'string', 'mode':'w'},
                )


    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'id'             : 'Company',
            'meta_type'      : 'Company',
            'description'    : """Arbitrary device grouping class""",
            'icon'           : 'Company_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addCompany',
            'immediate_view' : 'viewManufacturerOverview',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewManufacturerOverview'
                , 'permissions'   : (
                  CMFCorePermissions.View, )
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (
                  CMFCorePermissions.ModifyPortalContent, )
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


    def __init__(self, id,
        url = '',
        supportNumber = '',
        address1 = '',
        address2 = '',
        city = '',
        state = '',
        zip = ''):

        Instance.__init__(self, id)
        self.url = url
        self.supportNumber = supportNumber
        self.name = id
        self.address1 = address1
        self.address2 = address2
        self.city = city
        self.state = state
        self.zip = zip

InitializeClass(Company)
