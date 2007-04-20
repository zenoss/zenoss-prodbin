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

__doc__="""DeviceMap

DeviceMap maps the interface and ip tables to interface objects

$Id: DeviceMap.py,v 1.9 2003/11/19 03:14:53 edahl Exp $"""

__version__ = '$Revision: 1.9 $'[11:-2]

import re

from CollectorPlugin import SnmpPlugin, GetMap

class NewDeviceMap(SnmpPlugin):

    maptype = "NewDeviceMap" 

    snmpGetMap = GetMap({ 
             '.1.3.6.1.2.1.1.1.0' : 'snmpDescr',
             '.1.3.6.1.2.1.1.2.0' : 'snmpOid',
             })

    osregex = (
        #Novell NetWare 5.00.09 September 21, 2000 Proliant ML370
        re.compile(r'Novell (NetWare \S+)'),

        #Cisco Internetwork Operating System Software IOS (tm) s72033_rp Software (s72033_rp-IPSERVICESK9-M), Version 12.2(18)SXE3, RELEASE SOFTWARE (fc1) 
        re.compile(r'(IOS).*Version (\S+),'),           

        #Cisco Catalyst Operating System Software, Version 7.6(10)
        re.compile(r'(Cisco Catalyst).*Version (\S+)'), 

        #Cisco Systems, Inc./VPN 3000 Concentrator Version 4.1.7.D built 
        re.compile(r'(Cisco).*\/(VPN \d+).*Version (\S+)'), 

        #Hardware: x86 Family 15 Model 4 Stepping 1 AT/AT COMPATIBLE - Software: Windows Version 5.2 (Build 3790 Multiprocessor Free)
        re.compile(r'- Software: (.+) \(Build'),        

        #IBM PowerPC CHRP Computer Machine Type: 0x0800004c Processor id: 000919754C00 Base Operating System Runtime AIX version: 05.02.0000.0050 TCP/IP Client Support version: 05.02.0000.0051
        re.compile(r'^(IBM).*(AIX.*) TCP'),
   
        #GENERIC unix
        re.compile(r'(\S+) \S+ (\S+)'),                 # unix
    )


    def condition(self, device, log):
        """Only run if products have not been set.
        """
        return not device.os.getProductName() and not device.hw.getProductName()

    
    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing system info for device %s' % device.id)
        getdata, tabledata = results
        om = self.objectMap(getdata)
        om.setHWProductKey = om.snmpOid
        log.debug("HWProductKey=%s", om.setHWProductKey)
        descr = re.sub("\s", " ", om.snmpDescr)
        for regex in self.osregex:
            m = regex.search(descr)
            if m: 
                om.setOSProductKey = " ".join(m.groups())
                log.debug("OSProductKey=%s", om.setOSProductKey)
                break
        return om
