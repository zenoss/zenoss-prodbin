################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

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

from EventPopulator import EventPopulator
from MaintenanceThread import MaintenanceThread

registerDirectory('skins', globals())

zeneventpopulator = None
zeneventmaintenance = None

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
#    global zeneventpopulator
#    if not zeneventpopulator:
#        zeneventpopulator = EventPopulator()
#        zeneventpopulator.start()
#    global zeneventmaintenance
#    if not zeneventmaintenance:
#        zeneventmaintenance = MaintenanceThread()
#        zeneventmaintenance.start()
