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

from Products.ZenModel.ZenossSecurity import *

class TemperatureSensor(HWComponent):
    """TemperatureSensor object"""

    portal_type = meta_type = 'TemperatureSensor'

    state = "unknown"

    _properties = HWComponent._properties + (
        {'id':'state', 'type':'string', 'mode':'w'},
    )

    _relations = HWComponent._relations + (
        ("hw", ToOne(
            ToManyCont, "Products.ZenModel.DeviceHW", "temperaturesensors")),
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


    def temperatureCelsius(self, default=None):
        """
        Return the current temperature in degrees celsius
        """
        tempC = self.cacheRRDValue('temperature_celsius', default)
        if tempC is None:
            tempF = self.cacheRRDValue('temperature_fahrenheit', default)
            if tempF is not None: tempC = (tempF - 32) / 9 * 5
        if tempC is not None:
            return long(tempC)
        return None
    temperature = temperatureCelsius


    def temperatureFahrenheit(self, default=None):
        """
        Return the current temperature in degrees fahrenheit
        """
        tempC = self.temperatureCelsius(default)
        if tempC is not None:
            tempF = tempC * 9 / 5 + 32
            return long(tempF)
        return None


    def temperatureCelsiusString(self):
        """
        Return the current temperature in degrees celsius as a string
        """
        tempC = self.temperature()
        return tempC is None and "unknown" or "%dC" % (tempC,)
    temperatureString = temperatureCelsiusString


    def temperatureFahrenheitString(self):
        """
        Return the current temperature in degrees fahrenheit as a string
        """
        tempF = self.temperatureFahrenheit()
        return tempF is None and "unknown" or "%dF" % (tempF,)


    def viewName(self):
        return self.id
    name = viewName

InitializeClass(TemperatureSensor)
