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

__doc__ = """IPv6Network

Add an IPv6 network model for tracking IPv6 networks.
"""

import Migrate
from Products.ZenModel.IpNetwork import manage_addIpNetwork
from Products.Zuul.utils import safe_hasattr as hasattr

class addIpv6Network(Migrate.Step):
    version = Migrate.Version(4,0,0)

    def cutover(self, dmd):
        if not hasattr(dmd, 'IPv6Networks'):
            manage_addIpNetwork(dmd, "IPv6Networks", netmask=64, version=6)

# Add a variable so that other scripts can depend on
# this script
addIpv6NetworkInstance = addIpv6Network()

