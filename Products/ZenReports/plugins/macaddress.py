###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from Products.ZenReports.Utils import Record

class macaddress:
    ignoreInterfaces = ['lo', 'sit0']

    def run(self, dmd, args):
        report = []
        catalog = dmd.ZenLinkManager.layer2_catalog
        for brain in catalog():
            if brain.macaddress is None: # Bad catalog
                continue
            macaddress = brain.macaddress.upper()
            if not macaddress or macaddress == '00:00:00:00':
                continue
            ifaceName = brain.interfaceId.rsplit('/', 1)[-1]
            if ifaceName in self.ignoreInterfaces:
                continue
            deviceName = brain.deviceId.rsplit('/', 1)[-1]
            report.append(Record(
                            devicePath = brain.deviceId,
                            deviceName = deviceName,
                            interfacePath = brain.interfaceId,
                            interfaceName = ifaceName,
                            macaddress = brain.macaddress,
            ))
        return report

