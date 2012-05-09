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
from Products.ZenUtils.Utils import safe_hasattr as hasattr

class JobsDelete(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        jmgr = getattr(dmd, 'JobManager', None)
        if jmgr and hasattr(jmgr, 'jobs'):
            jmgr._delObject('jobs')

JobsDelete()
