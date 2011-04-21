###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """InterfaceAliasMap

    Extends the standard InterfaceMap to use the ifAlias as the interface's
    name instead of the ifDescr. This can be useful when many interfaces on
    the same device have the same ifDescr.
"""

from copy import deepcopy
from Products.DataCollector.plugins.zenoss.snmp.InterfaceMap \
    import InterfaceMap
from Products.DataCollector.plugins.CollectorPlugin import GetTableMap

class InterfaceAliasMap(InterfaceMap):
    
    snmpGetTableMaps = InterfaceMap.baseSnmpGetTableMaps + (
        # Extended interface information.
        GetTableMap('ifalias', '.1.3.6.1.2.1.31.1.1.1',
                {'.1' : 'ifName',
                 '.6' : 'ifHCInOctets',
                 '.7' : 'ifHCInUcastPkts',
                 '.15': 'highSpeed',
                 '.18': 'description'}
        ),
    )

    def __init__(self, *args, **kwargs):
        # save proxy to self as superclass, to guard against future
        # reload of plugin module changing imported classes (making
        # future super calls fail due to class mismatch)
        self.as_super = super(InterfaceAliasMap,self)
        self.as_super.__init__(*args, **kwargs)

    def process(self, device, results, log):
        """
        Pre-process the IF-MIB ifXTable to use the ifAlias as the interface's
        name instead of the ifDescr.
        """
        if 'ifalias' in results[1] and 'iftable' in results[1]:
            for a_idx, alias in results[1]['ifalias'].items():
                for i_idx, iface in results[1]['iftable'].items():
                    if a_idx == i_idx:
                        results[1]['iftable'][i_idx]['id'] = alias['ifName']
        
        return self.as_super.process(device, results, log)
