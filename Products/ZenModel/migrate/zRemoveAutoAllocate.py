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

import Migrate

class zRemoveAutoAllocate(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        if dmd.Networks.hasProperty('zAutoAllocateScript'):
            dmd.Networks._delProperty("zAutoAllocateScript")

zRemoveAutoAllocate()
