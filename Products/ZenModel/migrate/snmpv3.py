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
__doc__='Add zProperties for SNMPv3'

import Migrate
from Acquisition import aq_base

class SNMPv3(Migrate.Step):
    version = Migrate.Version(2, 1, 1)
    
    def cutover(self, dmd):
        devs = dmd.Devices
        for name in ("zSnmpSecurityName",
                     "zSnmpAuthPassword",
                     "zSnmpPrivPassword",
                     "zSnmpAuthType",
                     "zSnmpPrivType"):
            if not hasattr(aq_base(devs), name):
                devs._setProperty(name, "")

SNMPv3()

