###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__='''
Add zSnmpStrictDiscovery Z property.  If True, discoverDevices will not create
new devices for found IP's unless they return SNMP info
'''

import Migrate
import transaction

class addSnmpStrictDiscoveryFlag(Migrate.Step):
    version = Migrate.Version(2, 4, 0)

    def cutover(self, dmd):
        # Quick sanity check
        props = dmd.Networks.zenPropertyIds()
        if 'zSnmpStrictDiscovery' in props:
            return

        dmd.Networks._setProperty('zSnmpStrictDiscovery',False,'boolean')
        transaction.commit()


addSnmpStrictDiscoveryFlag()
