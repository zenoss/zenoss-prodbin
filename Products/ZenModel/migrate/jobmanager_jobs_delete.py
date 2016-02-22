##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate
from zope.component import getUtility
from Products.Zuul.catalog.interfaces import IModelCatalog, IModelCatalogTool
from Products.Zuul.utils import safe_hasattr as hasattr
import logging
log = logging.getLogger('zen.migrate')

class JobsDelete(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        jmgr = getattr(dmd, 'JobManager', None)
        if jmgr:
            model_catalog = getUtility(IModelCatalog).get_client(dmd)
            log.info("Removing old job records")
            for brain in IModelCatalogTool(dmd.JobManager).search():
                try:
                    if brain.getPath() != '/zport/dmd/JobManager':
                        model_catalog.uncatalog_object(brain.getObject())
                except Exception:
                    log.warn("Error removing %s", brain.getPath())
            log.info("Removing old job relationship")
            if hasattr(jmgr, 'jobs'):
                jmgr._delOb('jobs')

JobsDelete()
