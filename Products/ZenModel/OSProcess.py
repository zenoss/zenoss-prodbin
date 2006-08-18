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
        {'id':'zAlertOnRestarts', 'type':'boolean', 'mode':'w'},
        {'id':'zFailSeverity', 'type':'int', 'mode':'w'},
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
                { 'id'            : 'perfConf'
                , 'name'          : 'PerfConf'
                , 'action'        : 'objRRDTemplate'
                , 'permissions'   : ("Change Device", )
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

        thresholds = []
        try:
            templ = self.getRRDTemplate(self.getRRDTemplateName())
            if templ:
                threshs = self.getThresholds(templ)
                thresholds = threshs.items()
        except RRDObjectNotFound, e:
            log.warn(e)
        return (self.id, self.name(), 
                self.alertOnRestart(), self.failSeverity(),
                self.getStatus(), thresholds)


    def setOSProcessClass(self, procKey):
        """Set the OSProcessClass based on procKey which is the proc + args.
        We set by matching regular expressions of each proces class.
        """
        self.getDmdRoot("Processes").setOSProcessClass(self, procKey)
    

    def getOSProcessClass(self):
        """Return the current procKey.
        """
        return self.osProcessClass.getOrganizerName()
       

    def getRRDTemplateName(self):
        """Return list of graph urls.
        """
        return "OSProcess"


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


    def alertOnRestart(self):
        return self.getAqProperty("zAlertOnRestart")


    def failSeverity(self):
        """Return the severity for this service when it fails.
        """
        return self.getAqProperty("zFailSeverity")


    def getClassObject(self):
        return self.osProcessClass()


    security.declareProtected('Manage DMD', 'manage_editOSProcess')
    def manage_editOSProcess(self, zMonitor=False, zAlertOnRestart=False,
                             zFailSeverity=3, msg=None,REQUEST=None):
        """Edit a Service from a web page.
        """
        if msg is None: msg=[]
        msg.append(self.setAqProperty("zMonitor", zMonitor, "boolean"))
        msg.append(self.setAqProperty("zAlertOnRestart",zAlertOnRestart,"int"))
        msg.append(self.setAqProperty("zFailSeverity",zFailSeverity,"int"))
        msg = [ m for m in msg if m ]
        self.index_object()
        if not msg: msg.append("No action needed")
        if REQUEST:
            REQUEST['message'] = ", ".join(msg) + ":"
            return self.callZenScreen(REQUEST)


InitializeClass(OSProcess)
