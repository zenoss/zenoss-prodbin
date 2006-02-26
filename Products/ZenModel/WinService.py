#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions
from Acquisition import aq_base

from Products.ZenRelations.RelSchema import *

from Service import Service

class WinService(Service):
    """Windows Service Class
    """
    portal_type = meta_type = 'WinService'

    acceptPause = False
    acceptStop = False
    pathName = ""
    serviceType = ""
    startMode = ""
    startName = ""
    
    _relations = Service._relations + (
        ("os", ToOne(ToManyCont, "OperatingSystem", "winservices")),
    )

    factory_type_information = ( 
        { 
            'immediate_view' : 'winServiceDetail',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'winServiceDetail'
                , 'permissions'   : (
                  Permissions.view, )
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (
                  Permissions.view, )
                },
            )
         },
        )
    
    security = ClassSecurityInfo()
   
    
    def getInstDescription(self):
        """Return some text that describes this component.  Default is name.
        """
        return "'%s' StartMode:%s StartName:%s" % (self.caption(), 
                        self.startMode, self.startName)

        
    def getServiceClass(self):
        """Return a dict like one set by zenwinmodeler for services.
        """
        return {'name': self.name, 'description': self.description }


    def caption(self):
        """Return the windows caption for this service.
        """
        svccl = self.serviceclass()
        if svccl: return svccl.description
        return ""
    primarySortKey = caption


InitializeClass(WinService)

