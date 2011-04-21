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

__doc__="""PowerSupply

PowerSupply is an abstraction of a power supply on a device.

$Id: PowerSupply.py,v 1.7 2004/04/06 22:33:24 edahl Exp $"""

__version__ = "$Revision: 1.7 $"[11:-2]

from Globals import InitializeClass

from Products.ZenRelations.RelSchema import *

from HWComponent import HWComponent

from Products.ZenModel.ZenossSecurity import *

class PowerSupply(HWComponent):
    """PowerSupply object"""

    portal_type = meta_type = 'PowerSupply'

    watts = None
    type = "unknown"
    state = "unknown"

    _properties = HWComponent._properties + (
        {'id':'watts', 'type':'int', 'mode':'w'},
        {'id':'type', 'type':'string', 'mode':'w'},
        {'id':'state', 'type':'string', 'mode':'w'},
    )

    _relations = HWComponent._relations + (
        ("hw", ToOne(ToManyCont, "Products.ZenModel.DeviceHW",
            "powersupplies")),
        )

    
    factory_type_information = ( 
        { 
            'id'             : 'PowerSupply',
            'meta_type'      : 'PowerSupply',
            'description'    : """Arbitrary device grouping class""",
            'icon'           : 'PowerSupply_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addPowerSupply',
            'immediate_view' : 'viewPowerSupply',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'viewPowerSupply'
                , 'permissions'   : ('View',)
                },
                { 'id'            : 'perfConf'
                , 'name'          : 'Template'
                , 'action'        : 'objTemplates'
                , 'permissions'   : ("Change Device", )
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Modifications'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (ZEN_VIEW_MODIFICATIONS,)
                },
            )
          },
        )


    def wattsString(self):
        """
        Return a string representation of the watts
        """
        return self.watts is None and "unknown" or str(self.watts)


    def millivolts(self, default=None):
        """
        Return the current millivolts for the power supply
        """
        millivolts = self.cacheRRDValue('millivolts', default)
        if millivolts is not None:
            return long(millivolts)
        return None


    def millivoltsString(self):
        """
        Return the current millivolts as a string
        """
        millivolts = self.millivolts()
        return millivolts is None and "unknown" or "%dmv" % (millivolts,)


    def viewName(self):
        return self.id
    name = viewName


InitializeClass(PowerSupply)
