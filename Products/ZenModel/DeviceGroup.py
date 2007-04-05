#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""DeviceGroup


$Id: DeviceGroup.py,v 1.15 2004/04/04 01:51:19 edahl Exp $"""

__version__ = "$Revision: 1.15 $"[11:-2]

from Globals import DTMLFile
from Globals import InitializeClass

from Products.ZenRelations.RelSchema import *

from DeviceOrganizer import DeviceOrganizer

def manage_addDeviceGroup(context, id, description = None, REQUEST = None):
    """make a DeviceGroup"""
    d = DeviceGroup(id, description)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 


addDeviceGroup = DTMLFile('dtml/addDeviceGroup',globals())



class DeviceGroup(DeviceOrganizer):
    """
    DeviceGroup is a DeviceGroup Organizer that allows generic device groupings.
    """

    # Organizer configuration
    dmdRootName = "Groups"

    portal_type = meta_type = event_key = 'DeviceGroup'

    _relations = DeviceOrganizer._relations + (
        ("devices", ToMany(ToMany,"Products.ZenModel.Device","groups")),
        )

InitializeClass(DeviceGroup)
