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

import Zope
app = Zope.app()
#linux = app.zport.dmd.Devices.Servers.Linux._getOb('edahl04.confmon.loc')
win = app.zport.dmd.Devices.Servers.Windows._getOb('dhcp160.confmon.loc')
router = app.zport.dmd.Devices.NetworkDevices.Router._getOb(




