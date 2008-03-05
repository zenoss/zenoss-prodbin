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
import logging
log = logging.getLogger("zen.ActionRuleWindow")

import time

from Globals import DTMLFile
from AccessControl import ClassSecurityInfo
from Products.ZenModel.ZenossSecurity import *
from Products.ZenModel.MaintenanceWindow import MaintenanceWindow
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.Utils import unused

def manage_addActionRuleWindow(context, id, REQUEST=None):
    """Create an aciton rule"""
    ed = ActionRuleWindow(id)
    context._setObject(id, ed)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addActionRuleWindow = DTMLFile('dtml/addActionRuleWindow',globals())

class ActionRuleWindow(MaintenanceWindow):

    backCrumb = 'editActionRuleSchedule'      # FIXME

    actionRule = None
    
    factory_type_information = ( 
        { 
            'immediate_view' : 'actionRuleWindowDetail',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'actionRuleWindowDetail'
                , 'permissions'   : ( ZEN_VIEW, )
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Modifications'
                , 'action'        : 'viewHistory'
                , 'permissions'   : ( ZEN_VIEW, )
                },
            )
         },
        )
    
    _relations = (
        ("actionRule", ToOne(ToManyCont,"Products.ZenEvents.ActionRule","windows")),
        )
        
    security = ClassSecurityInfo()

    def target(self):
        return self.actionRule()

    def begin(self, now = None):
        self.target().enabled = True
        if not now:
            now = time.time()
        self.started = now

    def end(self):
        self.started = None
        self.target().enabled = False

    security.declareProtected(ZEN_CHANGE_ALERTING_RULES, 'manage_editActionRuleWindow')
    def manage_editActionRuleWindow(self,
                                     startDate='',
                                     startHours='',
                                     startMinutes='00',
                                     durationDays='0',
                                     durationHours='00',
                                     durationMinutes='00',
                                     repeat='Never',
                                     enabled=True,
                                     REQUEST=None, 
                                   **kw):
        "Update the ActionRuleWindow from GUI elements"
        unused(startDate, startHours, startMinutes,
               durationDays, durationHours, durationMinutes,
               repeat, kw, enabled)
        args = locals().copy()
        for name in 'self kw'.split(): del args[name]
        result = self.manage_editMaintenanceWindow(**args)
        try:
            del self.startProductionState
        except AttributeError:
            pass
        try:
            del self.stopProductionState
        except AttributeError:
            pass

        return result
