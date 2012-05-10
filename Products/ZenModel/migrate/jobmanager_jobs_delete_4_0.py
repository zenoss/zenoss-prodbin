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
from Products.Zuul.interfaces.tree import ICatalogTool
from Products.Zuul.utils import safe_hasattr as hasattr
import logging
log = logging.getLogger('zen.migrate')

class JobsDelete_4_0(Migrate.Step):
    version = Migrate.Version(4, 0, 0)

    def cutover(self, dmd):
        jmgr = getattr(dmd, 'JobManager', None)
        if jmgr:
            log.info("Removing old job records")
            for ob in ICatalogTool(dmd.JobManager).search():
                try:
                    if ob.getPath() != '/zport/dmd/JobManager':
                        dmd.global_catalog._catalog.uncatalogObject(ob.getPath())
                except Exception:
                    log.warn("Error removing %s", ob.getPath())
            log.info("Removing old job relationship")
            if hasattr(jmgr, 'jobs'):
                jmgr._delOb('jobs')


jobDelete_4_0 = JobsDelete_4_0()
