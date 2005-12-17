#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""SoftwareClass

SoftwareClass represents a software vendor's product.

$Id: SoftwareClass.py,v 1.5 2003/03/08 18:34:24 edahl Exp $"""

__version__ = "$Revision: 1.5 $"[11:-2]

from Globals import DTMLFile
from Globals import InitializeClass

from AccessControl import Permissions as permissions

from Products.ZenRelations.RelSchema import *

from ProductClass import ProductClass

def manage_addSoftwareClass(context, id, title = None, REQUEST = None):
    """make a SoftwareClass"""
    d = SoftwareClass(id, title)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addSoftwareClass = DTMLFile('dtml/addSoftwareClass',globals())

class SoftwareClass(ProductClass):
    """SoftwareClass object"""
    portal_type = meta_type = 'SoftwareClass'

    _properties = ProductClass._properties + (
        {'id':'version', 'type':'string', 'mode':'w'},
        {'id':'build', 'type':'string', 'mode':'w'},
        )

#    factory_type_information = ( 
#        { 
#            'id'             : 'SoftwareClass',
#            'meta_type'      : 'SoftwareClass',
#            'description'    : """Class to manage product information""",
#            'icon'           : 'SoftwareClass_icon.gif',
#            'product'        : 'ZenModel',
#            'factory'        : 'manage_addSoftwareClass',
#            'immediate_view' : 'viewProductOverview',
#            'actions'        :
#            ( 
#                { 'id'            : 'overview'
#                , 'name'          : 'Overview'
#                , 'action'        : 'viewSoftwareClassOverview'
#                , 'permissions'   : (
#                  permissions.view, )
#                },
#                { 'id'            : 'viewHistory'
#                , 'name'          : 'Changes'
#                , 'action'        : 'viewHistory'
#                , 'permissions'   : (
#                  permissions.view, )
#                },
#            )
#          },
#        )
    
    def __init__(self, id, title="", version="", build="", 
                partNumber="", description=""):
        ProductClass.__init__(self, id, title, partNumber, description)
        self.version = ""
        self.build = ""


InitializeClass(SoftwareClass)
