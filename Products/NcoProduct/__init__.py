################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

"""__init__

Initializer for netcool connector product

$Id: __init__.py,v 1.8 2004/04/22 19:08:47 edahl Exp $"""

__version__ = "$Revision: 1.8 $"[11:-2]

import Products.CMFCore
from Products.CMFCore.CMFCorePermissions import AddPortalContent
from Products.CMFCore.DirectoryView import registerDirectory

from NcoManager import NcoManager, manage_addNcoManager
from DmdNcoManager import DmdNcoManager, manage_addDmdNcoManager

factory_type_information = ()
contentClasses = ()
contentConstructors = ()

registerDirectory('skins', globals())

def initialize(registrar):
    registrar.registerClass(
        NcoManager,
        constructors = (manage_addNcoManager,)
        )
    registrar.registerClass(
        DmdNcoManager,
        constructors = (manage_addDmdNcoManager,)
        )
    
    #Products.CMFCore.utils.ContentInit(
    #            'NcoProduct', 
    #            content_types = contentClasses,
    #            permission = AddPortalContent,
    #            extra_constructors=contentConstructors,
    #            fti = factory_type_information,
    #            ).initialize(registrar)
