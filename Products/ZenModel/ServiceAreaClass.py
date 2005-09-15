#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""ServiceAreaClass

The servicearea classification class.  default identifiers, screens,
and data collectors live here.

$Id: ServiceAreaClass.py,v 1.9 2003/02/10 20:41:00 edahl Exp $"""

__version__ = "$Revision: 1.9 $"[11:-2]

from Globals import InitializeClass
from OFS.Folder import Folder
from Globals import DTMLFile

from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Classification import Classification

def manage_addServiceAreaClass(context, id, title = None, REQUEST = None):
    """make a device class"""
    dc = ServiceAreaClass(id, title)
    context._setObject(id, dc)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addServiceAreaClass = DTMLFile('dtml/addServiceAreaClass',globals())

class ServiceAreaClass(Classification, Folder):
    meta_type = "ServiceAreaClass"
    manage_main = Folder.manage_main
    manage_options = Folder.manage_options
    
    # default device screen
    view = PageTemplateFile('zpt/viewServiceAreaOverview.zpt',globals())
    devListMacro = PageTemplateFile('zpt/deviceListMacro.zpt',globals())
    isInTree = 0

InitializeClass(ServiceAreaClass)
