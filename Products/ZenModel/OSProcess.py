###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions
from Commandable import Commandable
from Products.ZenRelations.RelSchema import *
from Acquisition import aq_chain
from zExceptions import NotFound

from OSComponent import OSComponent
from ZenPackable import ZenPackable

def manage_addOSProcess(context, id, className, userCreated, REQUEST=None):
    """make an os process"""
    context._setObject(id, OSProcess(id))
    osp = context._getOb(id)
    setattr(osp, 'procName', id)
    if className == '/': className = ''
    orgPath = "/Processes%s" % className
    classPath = "%s/osProcessClasses/%s" % (orgPath, id)
    try:
        osp.getDmdObj(classPath)
    except (KeyError, NotFound):
        organizer = osp.getDmdObj(orgPath)
        organizer.manage_addOSProcessClass(id)
    osp.setOSProcessClass(classPath)
    if userCreated: osp.setUserCreateFlag()
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')

class OSProcess(OSComponent, Commandable, ZenPackable):
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

    _relations = OSComponent._relations + ZenPackable._relations + (
        ("os", ToOne(ToManyCont, "Products.ZenModel.OperatingSystem", "processes")),
        ("osProcessClass", ToOne(ToMany, "Products.ZenModel.OSProcessClass", "instances")),
        ('userCommands', ToManyCont(ToOne, 'Products.ZenModel.UserCommand', 'commandable')),
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
#                { 'id'            : 'perfConf'
#                , 'name'          : 'PerfConf'
#                , 'action'        : 'objRRDTemplate'
#                , 'permissions'   : ("Change Device", )
#                },
#                { 'id'            : 'manage'
#                , 'name'          : 'Manage'
#                , 'action'        : 'osProcessManage'
#                , 'permissions'   : ("Manage DMD",)
#                },
#                { 'id'            : 'viewHistory'
#                , 'name'          : 'Changes'
#                , 'action'        : 'viewHistory'
#                , 'permissions'   : ( Permissions.view, )
#                },
            )
         },
        )
    
    security = ClassSecurityInfo()

    def getOSProcessConf(self):
        """Return information used to monitor this process.
        """
        thresholds = {}
        for templ in self.getRRDTemplates():
            thresholds.update(self.getThresholds(templ))
        return (self.id, self.name(), self.osProcessClass().ignoreParameters,
                self.alertOnRestart(), self.getFailSeverity(), thresholds)

                    
    def setOSProcessClass(self, procKey):
        """Set the OSProcessClass based on procKey which is the proc + args.
        We set by matching regular expressions of each proces class.
        """
        klass = self.getDmdObj(procKey)
        klass.instances.addRelation(self)
    

    def getOSProcessClass(self):
        """Return the current procKey.
        """
        pClass = self.osProcessClass()
        if pClass:
            return pClass.getPrimaryDmdId()
       

    def getOSProcessClassLink(self):
        """Return an a link to the OSProcessClass.
        """
        proccl = self.osProcessClass()
        if proccl: return "<a href='%s'>%s</a>" % (proccl.getPrimaryUrlPath(),
                                                proccl.getOSProcessClassName())
        return ""

        
    def name(self):
        if not self.parameters or self.osProcessClass().ignoreParameters:
            return self.procName
        return self.procName + " " + self.parameters


    def monitored(self):
        """Should this service be monitored or not. Use ServiceClass aq path. 
        """
        return self.getAqProperty("zMonitor")


    def alertOnRestart(self):
        return self.getAqProperty("zAlertOnRestart")


    def getSeverities(self):
        """Return a list of tuples with the possible severities
        """
        return self.ZenEventManager.getSeverities()

    def getFailSeverity(self):
        """Return the severity for this service when it fails.
        """
        return self.getAqProperty("zFailSeverity")

    def getFailSeverityString(self):
        """Return a string representation of zFailSeverity
        """
        return self.ZenEventManager.severities[self.getAqProperty("zFailSeverity")]


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


    def getUserCommandTargets(self):
        ''' Called by Commandable.doCommand() to ascertain objects on which
        a UserCommand should be executed.
        '''
        return [self]     


    def getUserCommandEnvironment(self):
        environ = Commandable.getUserCommandEnvironment(self)
        context = self.primaryAq()
        environ.update({'proc': context,  'process': context,})
        return environ


    def getAqChainForUserCommands(self):
        chain = aq_chain(self.getClassObject().primaryAq())
        chain.insert(0, self)
        return chain


InitializeClass(OSProcess)
