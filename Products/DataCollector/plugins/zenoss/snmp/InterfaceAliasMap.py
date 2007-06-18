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

from InterfaceMap import InterfaceMap
from CollectorPlugin import GetTableMap


class InterfaceAliasMap(InterfaceMap):

    snmpGetTableMaps = (
        # If table
        GetTableMap('iftable', '.1.3.6.1.2.1.2.2.1', 
                {'.1': 'ifindex',
                 '.2': 'id',
                 '.3': 'type',
                 '.4': 'mtu',
                 '.5': 'speed',
                 '.6': 'macaddress',
                 '.7': 'adminStatus',
                 '.8': 'operStatus'}
        ),
        # Ip table
        GetTableMap('iptable', '.1.3.6.1.2.1.4.20.1',
                {'.1': 'ipAddress',
                 '.2': 'ifindex',
                 '.3': 'netmask'}
        ),
        # Interface Description
        GetTableMap('ifalias', '.1.3.6.1.2.1.31.1.1.1',
                {
                '.1': 'id',
                '.18' : 'description',
                '.15' : 'highSpeed',
                }
        ),
    )
