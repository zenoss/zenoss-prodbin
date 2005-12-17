#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__ = """CustomMap

CustomMap provides the interface for custom snmpcollector
plugins

$Id: CustomMap.py,v 1.4 2003/03/11 23:30:18 edahl Exp $"""

__version__ = '$Revision: 1.4 $'[11:-2]

import re

class CustomMap:

    prepId = re.compile(r'[^a-zA-Z0-9-_~,.$\(\)# ]')

    def condition(self, device, snmpsess):
        """does device meet the proper conditions for this collector to run"""
        return 0


    def collect(self, device, snmpsess, log):
        """collect snmp information from this device
        device is the a Device class (or subclass) object
        snmpsess is a valid instance of SnmpSession to connect
        to this device"""
        pass

    def description(self):
        """return a description of what this map does"""
        pass
