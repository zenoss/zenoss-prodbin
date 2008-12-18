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

Add zPreferSnmpNamingFlag z property.  If True, discovered devices will
use the snmp name (if found) instead of the dns name

$Id:$
'''
import Migrate
import transaction

class addPreferSnmpNamingFlag(Migrate.Step):
    version = Migrate.Version(2, 4, 0)

    def cutover(self, dmd):
        if not hasattr( dmd.Networks, 'zPreferSnmpNaming' ):
            dmd.Networks._setProperty( 'zPreferSnmpNaming', False,'boolean')
            transaction.commit()


addPreferSnmpNamingFlag()