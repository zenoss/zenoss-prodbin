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

__doc__="""DeviceGroup


$Id: DeviceGroup.py,v 1.15 2004/04/04 01:51:19 edahl Exp $"""

__version__ = "$Revision: 1.15 $"[11:-2]

from Globals import DTMLFile
from Globals import InitializeClass

from Products.ZenRelations.RelSchema import *

from DeviceOrganizer import DeviceOrganizer
from ZenPackable import ZenPackable

def manage_addDeviceGroup(context, id, description = None, REQUEST = None):
    """make a DeviceGroup"""
    d = DeviceGroup(id, description)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 


addDeviceGroup = DTMLFile('dtml/addDeviceGroup',globals())



class DeviceGroup(DeviceOrganizer, ZenPackable):
    """
    DeviceGroup is a DeviceGroup Organizer that allows generic device groupings.
    """

    # Organizer configuration
    dmdRootName = "Groups"

    portal_type = meta_type = event_key = 'DeviceGroup'

    _relations = DeviceOrganizer._relations + ZenPackable._relations + (
        ("devices", ToMany(ToMany,"Products.ZenModel.Device","groups")),
        )

InitializeClass(DeviceGroup)
