###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from copy import deepcopy
from Products.DataCollector.plugins.zenoss.snmp.InterfaceMap \
    import InterfaceMap
from Products.DataCollector.plugins.CollectorPlugin import GetTableMap

class InterfaceAliasMap(InterfaceMap):
    """
    Extends the standard InterfaceMap to use the ifAlias as the interface's
    name instead of the ifDescr. This can be useful when many interfaces on
    the same device have the same ifDescr.
    """
    
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
        
        return super(InterfaceAliasMap, self).process(device, results, log)
