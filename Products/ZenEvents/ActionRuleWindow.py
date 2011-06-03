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
import logging
log = logging.getLogger("zen.ActionRuleWindow")

from Globals import DTMLFile
from AccessControl import ClassSecurityInfo
from Products.ZenModel.MaintenanceWindow import MaintenanceWindow
from Products.ZenRelations.RelSchema import *

class ActionRuleWindow(MaintenanceWindow):

    backCrumb = 'editActionRuleSchedule'      # FIXME

    actionRule = None
    
    _relations = (
        ("actionRule", ToOne(ToManyCont,"Products.ZenEvents.ActionRule","windows")),
        )
        
    security = ClassSecurityInfo()
