#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""ServiceClass

The service classification class.  default identifiers, screens,
and data collectors live here.

$Id: ServiceClass.py,v 1.9 2003/03/11 23:32:13 edahl Exp $"""

__version__ = "$Revision: 1.9 $"[11:-2]

from Globals import InitializeClass
from OFS.Folder import Folder
from Globals import DTMLFile

from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Classification import Classification

def manage_addServiceClass(context, id, REQUEST = None):
    """make a device class"""
    dc = ServiceClass(id)
    context._setObject(id, dc)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addServiceClass = DTMLFile('dtml/addServiceClass',globals())

class ServiceClass(Classification, Folder):
    meta_type = "ServiceClass"
    manage_main = Folder.manage_main
    manage_options = Folder.manage_options
    
    # default service screen
    view = PageTemplateFile('zpt/viewServiceOverview.zpt',globals())

InitializeClass(ServiceClass)
