#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""Service.py

Service is a function provided by computer (like a server).  it
is defined by a protocol type (udp/tcp) and a port number.

$Id: Service.py,v 1.15 2003/03/11 23:32:13 edahl Exp $"""

__version__ = "$Revision: 1.15 $"[11:-2]

from Globals import DTMLFile
from Globals import InitializeClass
from Acquisition import aq_base
from AccessControl import ClassSecurityInfo

from Products.ZenRelations.RelSchema import *

from OSComponent import OSComponent

class Service(OSComponent):
    portal_type = meta_type = 'Service'
   
    _relations = OSComponent._relations + (
        ("serviceclass", ToOne(ToMany,"ServiceClass","instances")),
        )

    security = ClassSecurityInfo()

    def key(self):
        """Return tuple (manageIp, name) for this service to uniquely id it.
        """
        return (self.getManageIp(), self.name())


    def name(self):
        """Return the name of this service. (short name for net stop/start).
        """
        svccl = self.serviceclass()
        if svccl: return svccl.name
        return ""

    
    def monitored(self):
        """Should this service be monitored or not. Use ServiceClass aq path. 
        """
        return self._aqprop("zMonitor")


    def getFailSeverity(self):
        """Return the severity for this service when it fails.
        """
        return self._aqprop("zFailSeverity")


    def setServiceClass(self, name="", description=""):
        """Set the service class based on a dict describing the service.
        Dict keys are be protocol and port
        """
        srvs = self.dmd.getDmdRoot("Services")
        srvclass = srvs.createServiceClass(name=name, description=description)
        self.serviceclass.addRelation(srvclass)


    def getServiceClassLink(self):
        """Return an a link to the service class.
        """
        svccl = self.serviceclass()
        if svccl: return "<a href='%s'>%s</a>" % (svccl.getPrimaryUrlPath(),
                                                svccl.getServiceClassName())
        return ""


    def _aqprop(self, prop):
        """Get a property from ourself if it exsits then try serviceclass path.
        """
        if getattr(aq_base(self), prop, None) is not None:
            return getattr(self, prop)
        svccl = self.serviceclass()
        if svccl: 
            svccl = svccl.primaryAq()
            return getattr(svccl, prop)


    def _aqsetprop(self, prop, value, type):
        """Set a local prop if nessesaary on this service.
        """
        svccl = self.serviceclass()
        if not svccl: return
        svccl = svccl.primaryAq()
        svcval = getattr(svccl, prop)
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


    security.declareProtected('Manage DMD', 'manage_editService')
    def manage_editService(self,monitor=False,severity=5,msg=None,REQUEST=None):
        """Edit a Service from a web page.
        """
        if msg is None: msg=[]
        msg.append(self._aqsetprop("zMonitor", monitor, "boolean"))
        msg.append(self._aqsetprop("zFailSeverity", severity, "int"))
        msg = [ m for m in msg if m ]
        self.index_object()
        if not msg: msg.append("No action needed")
        if REQUEST:
            REQUEST['message'] = ", ".join(msg) + ":"
            return self.callZenScreen(REQUEST)


