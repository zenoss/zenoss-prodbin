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

import Migrate

class zZenDiscLove(Migrate.Step):
    version = Migrate.Version(2, 2, 0)
    
    def cutover(self, dmd):
        if not dmd.Networks.hasProperty('zAutoAllocateScript'):
            dmd.Networks._setProperty(
                "zAutoAllocateScript", ["#your python script here", "#avail objs: dmd, dev, log"], type="lines")
              
        if not dmd.Networks.hasProperty('zZenDiscCommand'):
            dmd.Networks._setProperty(
                "zZenDiscCommand", "zendisc run --net=${here/id}", type="string")


zZenDiscLove()
