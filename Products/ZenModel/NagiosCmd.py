#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

import os

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions
from DateTime import DateTime

from Products.PageTemplates.Expressions import getEngine
from Products.ZenUtils.ZenTales import talesCompile
from Products.ZenRelations.RelSchema import *

from ZenModelRM import ZenModelRM

def manage_addNagiosCmd(context, id, REQUEST = None):
    """make a NagiosCmd"""
    tt = NagiosCmd(id)
    context._setObject(tt.id, tt)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')


class NagiosCmd(ZenModelRM):

    usessh = True
    cycletime = 60
    enabled = True
    component = ""
    eventClass = "/Status/Nagios"
    eventKey = ""
    severity = 3
    commandTemplate = ""

    _properties = (
        {'id':'enabled', 'type':'boolean', 'mode':'w'},
        {'id':'usessh', 'type':'boolean', 'mode':'w'},
        {'id':'component', 'type':'string', 'mode':'w'},
        {'id':'eventClass', 'type':'string', 'mode':'w'},
        {'id':'severity', 'type':'int', 'mode':'w'},
        {'id':'commandTemplate', 'type':'string', 'mode':'w'},
    )

    _relations =  (
        ("nagiosTemplate", ToOne(ToManyCont, "NagiosTemplate", "nagiosCmds")),
    )    

    factory_type_information = ( 
        { 
            'immediate_view' : 'editNagiosCmd',
            'actions'        :
            ( 
                { 'name'          : 'Nagios Command'
                , 'action'        : 'editNagiosCmd'
                , 'permissions'   : ( Permissions.view, )
                },
                { 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : ( Permissions.view, )
                },
            )
         },
        )
    
    security = ClassSecurityInfo()


    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object add ActionRules list.
        [('url','id'), ...]
        """
        from NagiosTemplate import crumbspath
        crumbs = super(NagiosCmd, self).breadCrumbs(terminator)
        return crumbspath(self.nagiosTemplate(), crumbs, -2)


    def getCmdInfo(self, context):
        """Return tuple that defines monitored info for this cmd.
        (ssh,cycletime,compname,eventClass,eventKey,severity,commnad)
        """
        return (self.usessh, self.getCycleTime(context),
                self.getComponentName(context), self.eventClass, 
                self.eventKey, self.severity, self.getCommand(context))


    def getCycleTime(self, context):
        """Get cycle time of this monitor.
        """
        if self.cycletime != 0: return self.cycletime
        return context.zNagiosCycleTime
             
        
        
    def getComponentName(self, context):
        from DeviceComponent import DeviceComponent
        comp = self.component
        if isinstance(context, DeviceComponent):
            comp = context.name()
        return comp
   

    def getCommand(self, context):
        """Return localized command target.
        """
        """Perform a TALES eval on the express using context.
        """
        exp = "string:"+ self.commandTemplate
        compiled = talesCompile(exp)    
        device = context.device()
        environ = {'dev' : device, 'devname': device.id,
                    'here' : context, 
                    'compname' : self.getComponentName(context), 
                    'zNagiosPath' : context.zNagiosPath,
                    'nothing' : None, 'now' : DateTime() }
        res = compiled(getEngine().getContext(environ))
        if isinstance(res, Exception):
            raise res
        if not res.startswith(context.zNagiosPath):
            res = os.path.join(context.zNagiosPath, res)
        return res

InitializeClass(NagiosCmd)

