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

__doc__="""TemperatureSensor

TemperatureSensor is an abstraction of a temperature sensor or probe.

$Id: TemperatureSensor.py,v 1.7 2004/04/06 22:33:24 edahl Exp $"""

__version__ = "$Revision: 1.7 $"[11:-2]

from Globals import InitializeClass

from Products.ZenRelations.RelSchema import *

from HWComponent import HWComponent

class TemperatureSensor(HWComponent):
    """TemperatureSensor object"""

    portal_type = meta_type = 'TemperatureSensor'

    state = "unknown"

    _properties = HWComponent._properties + (
        {'id':'state', 'type':'string', 'mode':'w'},
    )

    _relations = HWComponent._relations + (
        ("hw", ToOne(ToManyCont, "Products.ZenModel.DeviceHW", "fans")),
        )

    
    factory_type_information = ( 
        { 
            'id'             : 'TemperatureSensor',
            'meta_type'      : 'TemperatureSensor',
            'description'    : """Arbitrary device grouping class""",
            'icon'           : 'TemperatureSensor_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addTemperatureSensor',
            'immediate_view' : 'viewTemperatureSensor',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'viewTemperatureSensor'
                , 'permissions'   : ('View',)
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Modifications'
                , 'action'        : 'viewHistory'
                , 'permissions'   : ('View',)
                },
            )
          },
        )

InitializeClass(TemperatureSensor)
