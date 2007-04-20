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

"""__init__

Initializer for netcool connector product

$Id: __init__.py,v 1.8 2004/04/22 19:08:47 edahl Exp $"""

__version__ = "$Revision: 1.8 $"[11:-2]

from Products.CMFCore.DirectoryView import registerDirectory

from MySqlEventManager import MySqlEventManager, addMySqlEventManager, \
    manage_addMySqlEventManager
from EventClass import EventClass, addEventClass, \
    manage_addEventClass
from EventClassInst import EventClassInst, addEventClassInst, \
    manage_addEventClassInst
from ActionRule import ActionRule, addActionRule, manage_addActionRule
from CustomEventView import CustomEventView, addCustomEventView, \
    manage_addCustomEventView
    

registerDirectory('skins', globals())

zeneventpopulator = None
zeneventmaintenance = None

productNames = (
    "ActionRule",
    "ActionRuleWindow",
    "EventClass",
    "EventClassInst",
    "EventCommand",
    "EventManagerBase",
)    

def initialize(registrar):
    registrar.registerClass(
        MySqlEventManager,
        constructors = (addMySqlEventManager, manage_addMySqlEventManager,)
        )
    registrar.registerClass(
        EventClass,
        permission="Add DMD Objects",
        icon = 'www/dict_icon.gif',
        constructors = (addEventClass, manage_addEventClass,)
        )
    registrar.registerClass(
        EventClassInst,
        permission="Add DMD Objects",
        icon = 'www/dict_rec_icon.gif',
        constructors = (addEventClassInst, manage_addEventClassInst,)
        )
    registrar.registerClass(
        ActionRule,
        permission="Add DMD Objects",
        constructors = (addActionRule, manage_addActionRule,)
        )
    registrar.registerClass(
        CustomEventView,
        permission="Add DMD Objects",
        constructors = (addCustomEventView, manage_addCustomEventView,)
        )
