###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__='Add zProperties for SNMPv3'

import Migrate
from Acquisition import aq_base

class snmpv3trap(Migrate.Step):
    version = Migrate.Version(3, 1, 70)
    
    def cutover(self, dmd):
        if not hasattr(aq_base(dmd.Devices), "zSnmpEngineId"):
            dmd.Devices._setProperty("zSnmpEngineId", "")

snmpv3trap()
