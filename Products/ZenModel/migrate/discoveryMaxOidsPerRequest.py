###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """When running network discovery, some devices can fail
during discovery/modeling due to requesting too many oids at one
time. When adding a device to a device class, the zProperty named
'zMaxOIDPerRequest' can be used to modify the request for the device
types we know have this problem. In discovery, however, we don't know
what the target device type is, so the property needs to be reduced
for the '/Discovered' device class. This migrate scripts reduces the
default zMaxOIDPerRequest in /Discovered to 10"""

import logging
import Globals
from Products.ZenUtils.Utils import unused
from Products.ZenModel.migrate import Migrate
from zExceptions import BadRequest

unused(Globals)

log = logging.getLogger('zen.migrate')



class discoveryMaxOidsPerRequest(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        try:
            disc = dmd.Devices.Discovered
            if not disc.isLocal('zMaxOIDPerRequest'):
                disc.setZenProperty('zMaxOIDPerRequest', 10)
                log.info("Setting zMaxOIDPerRequest to 10 on /Discovered")
        except (AttributeError, BadRequest):
            # they might not have discovery or this zproperty
            log.warn("Unable to set the zMaxOidsPerRequest on /Discovered")


discoveryMaxOidsPerRequest()
