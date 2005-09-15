#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""ServiceArea

Physical area to which a service is provided. ie CILI code
or region like LI, NJ, CT

$Id: ServiceArea.py,v 1.10 2002/07/19 16:35:18 alex Exp $"""

__version__ = "$Revision: 1.10 $"[11:-2]

from Globals import DTMLFile
from Globals import InitializeClass

from Instance import Instance

def manage_addServiceArea(context, id, title = None, REQUEST = None):
    """make a ServiceArea"""
    d = ServiceArea(id, title)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addServiceArea = DTMLFile('dtml/addServiceArea',globals())

class ServiceArea(Instance):
    """ServiceArea object"""
    meta_type = 'ServiceArea'
    _properties = (
                    {'id':'description', 'type':'text', 'mode':'w'},
                   ) 

    def __init__(self, id, title = None):
        Instance.__init__(self, id, title)
        self.description = ''

InitializeClass(ServiceArea)

class CiliCode(ServiceArea):
    meta_type = 'CiliCode'
    _properties = (
                    {'id':'city', 'type':'text', 'mode':'w'},
                    {'id':'state', 'type':'text', 'mode':'w'},
                   ) + ServiceArea._properties

    def __init__(self, id, title=None, description=None, city=None, state=None):
        ServiceArea.__init__(self, id, title, description)
        self.city = city
        self.state = state

InitializeClass(CiliCode)
