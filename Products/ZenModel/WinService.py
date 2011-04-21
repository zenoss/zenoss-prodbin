###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions
from Products.ZenModel.ZenossSecurity import *

from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.Utils import prepId
from Products.ZenWidgets import messaging
from Products.ZenModel.WinServiceClass import WinServiceClass
from Service import Service

def manage_addWinService(context, id, description, userCreated=None, 
                         REQUEST=None):
    """
    Create a WinService and add it to context. context should be a
    device.os.winservices relationship.
    """
    s = WinService(id)
    # Indexing is subscribed to ObjectAddedEvent, which fires
    # on _setObject, so we want to set service class first.
    args = {'name':id, 'description':description}
    s.__of__(context).setServiceClass(args)
    context._setObject(id, s)
    s = context._getOb(id)
    s.serviceName = id
    s.caption = description
    if userCreated: s.setUserCreateFlag()
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                  +'/manage_main')
    return s


class WinService(Service):
    """Windows Service Class
    """
    portal_type = meta_type = 'WinService'

    serviceName = ""
    caption = ""
    pathName = ""
    serviceType = ""
    startMode = ""
    startName = ""
    monitoredStartModes = []
    collectors = ('zenwin',)

    _properties = Service._properties + (
        {'id': 'serviceName', 'type':'string', 'mode':'w'},
        {'id': 'caption', 'type':'string', 'mode':'w'},
        {'id': 'pathName', 'type':'string', 'mode':'w'},
        {'id': 'serviceType', 'type':'string', 'mode':'w'},
        {'id': 'startMode', 'type':'string', 'mode':'w'},
        {'id': 'startName', 'type':'string', 'mode':'w'},
        {'id': 'monitoredStartModes', 'type':'lines', 'mode':'w'},
    )

    _relations = Service._relations + (
        ("os", ToOne(ToManyCont, "Products.ZenModel.OperatingSystem", "winservices")),
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
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'viewEvents'
                , 'permissions'   : (ZEN_VIEW, )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Administration'
                , 'action'        : 'winServiceManage'
                , 'permissions'   : ("Manage DMD",)
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Modifications'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (ZEN_VIEW_MODIFICATIONS,)
                },
            )
         },
        )

    security = ClassSecurityInfo()


    def getInstDescription(self):
        """Return some text that describes this component.  Default is name.
        """
        return "'%s' StartMode:%s StartName:%s" % (self.caption,
                        self.startMode, self.startName)


    def getMonitoredStartModes(self):
        if self.monitoredStartModes:
            return self.monitoredStartModes
        return self.serviceclass().monitoredStartModes


    def monitored(self):
        """Should this Windows Service be monitored
        """
        startMode = getattr(self, "startMode", None)
        #don't monitor Disabled services
        if startMode and startMode == "Disabled": return False
        return Service.monitored(self)


    def getStatus(self, statClass=None):
        """
        Return the status number for this WinService
        """
        if self.startMode not in self.getMonitoredStartModes():
            return -1
        return Service.getStatus(self, statClass)


    def getServiceClass(self):
        """Return a dict like one set by zenwinmodeler for services.
        """
        desc = self.description
        if not desc:
            svccl = self.serviceclass()
            if svccl: desc = svccl.description
        return {'name': self.serviceName, 'description': self.caption }


    def setServiceClass(self, kwargs):
        """Set the service class where name=ServiceName and description=Caption.
        """
        self.serviceName = kwargs['name']
        self.caption = kwargs['description']
        path = "/WinService/"
        srvs = self.dmd.getDmdRoot("Services")
        srvclass = srvs.createServiceClass(
            name=self.serviceName, description=self.caption, path=path, factory=WinServiceClass)
        self.serviceclass.addRelation(srvclass)


    def name(self):
        """Return the name of this service.
        """
        return self.serviceName

    def getCaption(self):
        return self.caption
    primarySortKey = getCaption

    security.declareProtected('Manage DMD', 'manage_editService')
    def manage_editService(self, id=None, description=None, 
                            pathName=None, serviceType=None,
                            startMode=None, startName=None,
                            monitoredStartModes=[],
                            monitor=False, severity=5, 
                            REQUEST=None):
        """Edit a Service from a web page.
        """
        msg = []
        renamed = False
        if id is not None:
            self.serviceName = id
            self.description = description
            self.caption = description
            self.pathName = pathName
            self.serviceType = serviceType
            self.startMode = startMode
            self.startName = startName

            if self.id != id:
                id = prepId(id)
                self.setServiceClass(dict(name=id, description=description))
                renamed = self.rename(id)

        if set(monitoredStartModes) != set(self.getMonitoredStartModes()):
            self.monitoredStartModes = monitoredStartModes
            msg.append("Updated monitored start modes")

        tmpl = super(WinService, self).manage_editService(
            monitor, severity, msg=msg, REQUEST=REQUEST)
        if REQUEST and renamed:
            messaging.IMessageSender(self).sendToBrowser(
                'Service Renamed',
                "Object renamed to: %s" % self.id
            )
            return self.callZenScreen(REQUEST, renamed)
        return tmpl

InitializeClass(WinService)

