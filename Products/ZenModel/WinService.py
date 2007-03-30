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

def manage_addWinService(context, id, description, userCreated=None, REQUEST=None):
    """make a device"""
    s = WinService(id)
    context._setObject(id, s)
    s = context._getOb(id)
    setattr(s, 'name', id)
    setattr(s, 'description', description)
    args = {'name':id, 'description':description}
    s.setServiceClass(args)
    if userCreated: s.setUserCreateFlag()
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                  +'/manage_main')
                                                                                                           
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
   
    _properties = Service._properties + (
        {'id': 'acceptPause', 'type':'boolean', 'mode':'w'},
        {'id': 'acceptStop', 'type':'boolean', 'mode':'w'},
        {'id': 'pathName', 'type':'string', 'mode':'w'},
        {'id': 'serviceType', 'type':'string', 'mode':'w'},
        {'id': 'startMode', 'type':'string', 'mode':'w'},
        {'id': 'startName', 'type':'string', 'mode':'w'},
    )

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
                #{ 'id'            : 'manage'
                #, 'name'          : 'Manage'
                #, 'action'        : 'winServiceManage'
                #, 'permissions'   : ("Manage DMD",)
                #},
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


    def setServiceClass(self, kwargs):
        """Set the service class based on a dict describing the service.
        Dict keys are be name and description. where name=ServiceName
        and description=Caption.
        """
        name = kwargs['name']
        description = kwargs['description']
        path = "/WinService/"
        srvs = self.dmd.getDmdRoot("Services")
        srvclass = srvs.createServiceClass(name=name, description=description, 
                                           path=path)
        self.serviceclass.addRelation(srvclass)


    def caption(self):
        """Return the windows caption for this service.
        """
        svccl = self.serviceclass()
        if svccl: return svccl.description
        return ""
    primarySortKey = caption

    security.declareProtected('Manage DMD', 'manage_editService')
    def manage_editService(self, status, 
                            name, description, 
                            acceptPause, acceptStop,
                            pathName, serviceType,
                            startMode, startName,
                            monitor=False, severity=5, 
                            REQUEST=None):
        """Edit a Service from a web page.
        """
        serviceClassChanged = False
        if name != self.name:
            serviceClassChanged = True
            self.winservices._remoteRemove(self)
            setattr(self, 'name', name)
            setattr(self, 'id', name)
            self.winservices._setObject(name, self)

        if description != self.description:
            serviceClassChanged = True
            setattr(self, 'description', description)
        
        if serviceClassChanged:
            self.setServiceClass({'name':name, 'description':description})
        
        setattr(self, 'status', status)
        setattr(self, 'acceptPause', acceptPause)
        setattr(self, 'acceptStop', acceptStop)
        setattr(self, 'pathName', pathName)
        setattr(self, 'serviceType', serviceType)
        setattr(self, 'startMode', startMode)
        setattr(self, 'startName', startName)
        
        return super(WinService, self).manage_editService(monitor, severity, 
                                    REQUEST=REQUEST)

InitializeClass(WinService)

