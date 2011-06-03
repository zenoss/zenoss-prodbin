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

from AccessControl import ClassSecurityInfo
from Acquisition import aq_parent
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenModel.Commandable import Commandable
from Products.ZenModel.ZenPackable import ZenPackable
from Products.ZenRelations.RelSchema import *
from Globals import InitializeClass
from EventFilter import EventFilter

class EventCommand(ZenModelRM, Commandable, EventFilter, ZenPackable):

    where = ''
    command = ''
    clearCommand = ''
    enabled = False
    delay = 0
    repeatTime = 0
    
    _properties = ZenModelRM._properties + (
        {'id':'command', 'type':'string', 'mode':'w'},
        {'id':'clearCommand', 'type':'string', 'mode':'w'},
        {'id':'where', 'type':'string', 'mode':'w'},
        {'id':'defaultTimeout', 'type':'int', 'mode':'w'},
        {'id':'enabled', 'type':'boolean', 'mode':'w'},
        {'id':'delay', 'type':'int', 'mode':'w'},
        {'id':'repeatTime', 'type':'int', 'mode':'w'},
    )
    
    _relations =  ZenPackable._relations + (
        ("eventManager", ToOne(ToManyCont, "Products.ZenEvents.EventManagerBase", "commands")),
    )

    security = ClassSecurityInfo()
        
    
InitializeClass(EventCommand)

