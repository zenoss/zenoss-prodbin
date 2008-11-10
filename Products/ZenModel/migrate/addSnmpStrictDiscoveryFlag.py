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

Add zSnmpStrictDiscovery z property.  If True, discoverDevices will not create
new devices for found ip's unless they return snmp info

$Id:$
'''
import Migrate
import transaction

class addSnmpStrictDiscoveryFlag(Migrate.Step):
    version = Migrate.Version(2, 3, 0)

    def cutover(self, dmd):
        dmd.Networks._setProperty('zSnmpStrictDiscovery',False,'boolean')
        transaction.commit()


addSnmpStrictDiscoveryFlag()