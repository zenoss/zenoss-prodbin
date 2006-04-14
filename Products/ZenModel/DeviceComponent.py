#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""DeviceComponent

All device components inherit from this class

$Id: DeviceComponent.py,v 1.1 2004/04/06 21:05:03 edahl Exp $"""

__version__ = "$Revision: 1.1 $"[11:-2]

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo


class DeviceComponent(object):
    """
    DeviceComponent is a mix-in class for all components of a device.
    These include LogicalComponent, Software, and Hardware.
    """
    event_key = "Component"

    default_catalog = "componentSearch"

    security = ClassSecurityInfo()

    def getParentDeviceName(self):
        """return the name of this component's device"""
        name = ""
        dev = self.device()
        if dev: name = dev.getDeviceName()
        return name
    hostname = getParentDeviceName

    def getParentDeviceUrl(self):
        """return the url of this component's device"""
        url = ""
        dev = self.device()
        if dev: url = dev.absolute_url()
        return url
    
   
    def name(self):
        """Return the name of this component.  Default is id.
        """
        return self.id


    def monitored(self):
        """Return the monitored status of this component. Default is False.
        """
        return False


    def getInstDescription(self):
        """Return some text that describes this component.  Default is name.
        """
        return self.name()

        
    def getStatus(self, statClass=None):
        """Return the status number for this component of class statClass.
        """
        if not self.monitored(): return -1
        if not statClass: statClass = "/Status/%s" % self.meta_type
        return self.getEventManager().getComponentStatus(
                self.getParentDeviceName(), self.name(), statclass=statClass)
  

    def getManageIp(self):
        """Return the manageIP of the device of this component.
        """
        dev = self.device()
        if dev: return dev.getManageIp()
        return ""

    
    def manage_afterAdd(self, item, container):
        """
        Device only propagates afterAdd if it is the added object.
        """
        self.index_object()
        super(DeviceComponent,self).manage_afterAdd(item, container)


    def manage_afterClone(self, item):
        """Not really sure when this is called."""
        super(DeviceComponent,self).manage_afterClone(item)
        self.index_object()


    def manage_beforeDelete(self, item, container):
        """
        Device only propagates beforeDelete if we are being deleted or copied.
        Moving and renaming don't propagate.
        """
        super(DeviceComponent,self).manage_beforeDelete(item, container)
        self.unindex_object()


    def index_object(self):
        """A common method to allow Findables to index themselves."""
        cat = getattr(self, self.default_catalog, None)
        if cat != None: 
            cat.catalog_object(self, self.getPrimaryId())
            
                                                
    def unindex_object(self):
        """A common method to allow Findables to unindex themselves."""
        cat = getattr(self, self.default_catalog, None)
        if cat != None: 
            cat.uncatalog_object(self.getPrimaryId())



InitializeClass(DeviceComponent)
