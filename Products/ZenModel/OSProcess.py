#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions

from Products.ZenRelations.RelSchema import *

from OSComponent import OSComponent

class OSProcess(OSComponent):
    """Hardware object"""
    portal_type = meta_type = 'OSProcess'

    procName = ""
    parameters = ""
    _procKey = ""

    _properties = OSComponent._properties + (
        {'id':'procName', 'type':'string', 'mode':'w'},
        {'id':'parameters', 'type':'string', 'mode':'w'},
        {'id':'zCountProcs', 'type':'boolean', 'mode':'w'},
        {'id':'zAlertOnRestarts', 'type':'boolean', 'mode':'w'},
    )

    _relations = OSComponent._relations + (
        ("os", ToOne(ToManyCont, "OperatingSystem", "processes")),
        ("osProcessClass", ToOne(ToMany, "OSProcessClass", "instances")),
    )

    factory_type_information = ( 
        { 
            'immediate_view' : 'osProcessDetail',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'osProcessDetail'
                , 'permissions'   : ( Permissions.view, )
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : ( Permissions.view, )
                },
            )
         },
        )
    
    security = ClassSecurityInfo()

    def getOSProcessConf(self):
        """Return information used to monitor this process.
        """
        return (self.id, self.name(), self.countProcs(), self.alertOnRestart())


    def setOSProcessClass(self, procKey):
        """Set the OSProcessClass based on procKey which is the proc + args.
        We set by matching regular expressions of each proces class.
        """
        self._procKey = self.getDmdRoot("Processes").setOSProcessClass(
                                self, procKey)
        return self._procKey
    

    def getOSProcessClass(self):
        """Return the current procKey.
        """
        return self._procKey
       

    def getPerformanceTargetType(self):
        """Return list of graph urls.
        """
        return self.countProcs() and "OSProcessCount" or "OSProcess"


    def getOSProcessClassLink(self):
        """Return an a link to the OSProcessClass.
        """
        proccl = self.osProcessClass()
        if proccl: return "<a href='%s'>%s</a>" % (proccl.getPrimaryUrlPath(),
                                                proccl.getOSProcessClassName())
        return ""

        
    def name(self):
        return self.procName + " " + self.parameters


    def monitored(self):
        """Should this service be monitored or not. Use ServiceClass aq path. 
        """
        return self.getAqProperty("zMonitor")


    def countProcs(self):
        return self.getAqProperty("zCountProcs")


    def alertOnRestart(self):
        return self.getAqProperty("zAlertOnRestart")


    def getClassObject(self):
        return self.osProcessClass()


    security.declareProtected('Manage DMD', 'manage_editOSProcess')
    def manage_editOSProcess(self, zMonitor=False, zCountProcs=False,
                            zAlertOnRestart=False, msg=None,REQUEST=None):
        """Edit a Service from a web page.
        """
        if msg is None: msg=[]
        msg.append(self.setAqProperty("zMonitor", zMonitor, "boolean"))
        msg.append(self.setAqProperty("zCountProcs", zCountProcs, "int"))
        msg.append(self.setAqProperty("zAlertOnRestart",zAlertOnRestart,"int"))
        msg = [ m for m in msg if m ]
        self.index_object()
        if not msg: msg.append("No action needed")
        if REQUEST:
            REQUEST['message'] = ", ".join(msg) + ":"
            return self.callZenScreen(REQUEST)


InitializeClass(OSProcess)
