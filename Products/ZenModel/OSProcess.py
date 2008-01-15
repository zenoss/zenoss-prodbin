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

from OSComponent import OSComponent
from ZenPackable import ZenPackable


def manage_addOSProcess(context, className, userCreated, REQUEST=None):
    """
    Make an os process from the ZMI
    """
    id = className.split('/')[-1]
    context._setObject(id, OSProcess(id))
    osp = context._getOb(id)
    osp.procName = id
    osp.setOSProcessClass(className)
    if userCreated: osp.setUserCreateFlag()
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
    return osp


def createFromObjectMap(context, objectMap):
    import md5
    om = objectMap
    device = context.device()
    processes = context.device().getDmdRoot("Processes")
    pcs = processes.getSubOSProcessClassesSorted()
    fullname = (om.procName + ' ' + om.parameters).rstrip()
    for pc in pcs:
        if pc.match(fullname):
            id = om.procName
            parameters = om.parameters.strip()
            if parameters and not pc.ignoreParameters:
                parameters = md5.md5(parameters).hexdigest()
                id += ' ' + parameters
            result = OSProcess(device.prepId(id))
            om.setOSProcessClass = pc.getPrimaryDmdId()
            return result


class OSProcess(OSComponent, Commandable, ZenPackable):
    """
    OSProcess object
    """
    portal_type = meta_type = 'OSProcess'

    procName = ""
    parameters = ""
    _procKey = ""
    collectors = ('zenprocess', )

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
                { 'id'            : 'perfConf'
                , 'name'          : 'Template'
                , 'action'        : 'objTemplates'
                , 'permissions'   : ("Change Device", )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Administration'
                , 'action'        : 'osProcessManage'
                , 'permissions'   : ("Manage DMD",)
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Modifications'
                , 'action'        : 'viewHistory'
                , 'permissions'   : ( Permissions.view, )
                },
            )
         },
        )
    
    security = ClassSecurityInfo()


    def getOSProcessConf(self):
        """
        Return information used to monitor this process.
        """
        ignoreParams = getattr(self.osProcessClass(), 'ignoreParameters', False)
        return (self.id, self.name(), ignoreParams,
                self.alertOnRestart(), self.getFailSeverity())


    def setOSProcessClass(self, procKey):
        """
        Set the OSProcessClass based on procKey which is the proc + args.
        We set by matching regular expressions of each proces class.
        """
        klass = self.getDmdObj(procKey)
        klass.instances.addRelation(self)
    

    def getOSProcessClass(self):
        """
        Return the current procKey.
        """
        pClass = self.osProcessClass()
        if pClass:
            return pClass.getPrimaryDmdId()
       

    def getOSProcessClassLink(self):
        """
        Return an a link to the OSProcessClass.
        """
        proccl = self.osProcessClass()
        if proccl:
            if self.checkRemotePerm("View", proccl): 
                return "<a href='%s'>%s</a>" % (proccl.getPrimaryUrlPath(),
                                                proccl.getOSProcessClassName())
            else:
                return proccl.getOSProcessClassName()
        return ""

        
    def name(self):
        """
        Return a string that is the process name and, if ignoreParamaters
        is not True, then also the parameters.
        """
        ignoreParams = getattr(self.osProcessClass(), 'ignoreParameters', False)
        if not self.parameters or ignoreParams:
            return self.procName
        return self.procName + " " + self.parameters


    def monitored(self):
        """
        Should this service be monitored or not. Use ServiceClass aq path. 
        """
        return self.getAqProperty("zMonitor")


    def alertOnRestart(self):
        """
        Retrieve the zProperty zAlertOnRestart
        """
        return self.getAqProperty("zAlertOnRestart")


    def getSeverities(self):
        """
        Return a list of tuples with the possible severities
        """
        return self.ZenEventManager.getSeverities()


    def getFailSeverity(self):
        """
        Return the severity for this service when it fails.
        """
        return self.getAqProperty("zFailSeverity")


    def getFailSeverityString(self):
        """
        Return a string representation of zFailSeverity
        """
        return self.ZenEventManager.severities[self.getAqProperty("zFailSeverity")]


    def getClassObject(self):
        """
        Return the ProcessClass for this proc
        """
        return self.osProcessClass()


    security.declareProtected('Manage DMD', 'manage_editOSProcess')
    def manage_editOSProcess(self, zMonitor=False, zAlertOnRestart=False,
                             zFailSeverity=3, msg=None,REQUEST=None):
        """
        Edit a Service from a web page.
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
        '''
        Called by Commandable.doCommand() to ascertain objects on which
        a UserCommand should be executed.
        '''
        return [self]     


    def getUserCommandEnvironment(self):
        """
        Return the environment to be used when processing a UserCommand
        """
        environ = Commandable.getUserCommandEnvironment(self)
        context = self.primaryAq()
        environ.update({'proc': context,  'process': context,})
        return environ


    def getAqChainForUserCommands(self):
        """
        Setup the aq chain as appropriate for the execution of a UserCommand
        """
        chain = aq_chain(self.getClassObject().primaryAq())
        chain.insert(0, self)
        return chain
        
        
    def getUrlForUserCommands(self):
        """
        Return the url where UserCommands are viewed for this object
        """
        return self.getPrimaryUrlPath() + '/osProcessManage'

    def filterAutomaticCreation(self):
	#get the processes defined in Zenoss
        processes = self.getDmdRoot("Processes")
        pcs = list(processes.getSubOSProcessClassesGen())
        pcs.sort(lambda a, b: cmp(a.sequence,b.sequence))
      
        for pc in pcs:
            fullname = (self.procName + ' ' + self.parameters).rstrip()
            if pc.match(fullname):
                self.setOSProcessClass(pc.getPrimaryDmdId())
                self.id = om.procName
                parameters = om.parameters.strip()
                if parameters and not pc.ignoreParameters:
                    parameters = md5.md5(parameters).hexdigest()
                    self.id += ' ' + parameters
                self.id = self.prepId(id)
                return True
        return False


InitializeClass(OSProcess)
