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
from Acquisition import aq_base
from Lockable import Lockable
from Products.ZenEvents.ZenEventClasses import Change_Add,Change_Remove,Change_Set

class DeviceComponent(Lockable):
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
        return self.monitor


    def getInstDescription(self):
        """Return some text that describes this component.  Default is name.
        """
        return self.name()

        
    def getStatus(self, statClass=None):
        """Return the status number for this component of class statClass.
        """
        if not self.monitored() or not self.device().monitorDevice(): return -1
        if not statClass: statClass = "/Status/%s" % self.meta_type
        return self.getEventManager().getComponentStatus(
                self.getParentDeviceName(), self.name(), statclass=statClass)

  
    def getStatusString(self, statClass=None):
        return self.convertStatus(self.getStatus(statClass))


    def getManageIp(self):
        """Return the manageIP of the device of this component.
        """
        dev = self.device()
        if dev: return dev.getManageIp()
        return ""

    
    def getRRDTemplateByName(self, name):
        """Return the closest RRDTemplate named name by walking our aq chain.
        """
        try:
            return getattr(self, name)
        except AttributeError:
            return super(DeviceComponent, self).getRRDTemplateByName(name)


    def getNagiosTemplate(self, name=None):
        import warnings
        warnings.warn('anything named nagios is deprecated', DeprecationWarning)


    def getAqProperty(self, prop):
        """Get a property from ourself if it exsits then try serviceclass path.
        """
        if getattr(aq_base(self), prop, None) is not None:
            return getattr(self, prop)
        classObj = self.getClassObject()
        if classObj: 
            classObj = classObj.primaryAq()
            return getattr(classObj, prop)


    def setAqProperty(self, prop, value, type):
        """Set a local prop if nessesaary on this service.
        """
        classObj = self.getClassObject()
        if not classObj: return
        classObj = classObj.primaryAq()
        svcval = getattr(classObj, prop)
        locval = getattr(aq_base(self),prop,None)
        msg = ""
        if svcval == value and locval is not None:
            self._delProperty(prop)
            msg = "Removed local %s" % prop
        elif svcval != value and locval is None:
            self._setProperty(prop, value, type=type)
            msg = "Set local %s" % prop
        elif locval is not None and locval != value:
            setattr(self, prop, value)
            msg = "Update local %s" % prop
        return msg

    
    def getClassObject(self):
        """If you are going to use acquisition up different class path
        override this.
        """
        return self.device()


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
        
InitializeClass(DeviceComponent)
