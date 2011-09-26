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

import Globals
import sys
import Migrate
import zExceptions

import logging
log = logging.getLogger("zen.migrate")
from Products.ZEnUtils.debugtools import profile

import time

class RebuildPathIndex(Migrate.Step):
    version = Migrate.Version(4, 0, 0)

    def cutover(self, dmd):
        if getattr(dmd, "_pathReindexed", None) is not None:
            log.info('path has already been reindexed')
            return
        zport = dmd.getPhysicalRoot().zport
        tstart=time.time()
        starttotal = time.time()
        i = 0
        # global catalog
        CHUNK_SIZE = 200 if sys.stdout.isatty() else 25000 # Don't be chatty when logging to a file
        for x in zport.global_catalog():
            i+=1
            try:
                # we updated how ipaddresses and path were stored so re-catalog them
                zport.global_catalog.catalog_object(x.getObject(),x.getPath(),
                                                    idxs=['path', 'ipAddress'],
                                                    update_metadata=False)
            except TypeError:
                # work around for bad data
                log.warning("Unable to index %s " % x.getPath())
            except (KeyError, zExceptions.NotFound):
                zport.global_catalog.uncatalog_object(x.getPath())
            if i % CHUNK_SIZE == 0:
                self.log_progress("rate=%.2f/sec count=%d" %
                                  (CHUNK_SIZE/(time.time()-tstart), i))
                tstart=time.time()
        print
        log.info("Finished total time=%.2f rate=%.2f count=%d",
                time.time()-starttotal, i/(time.time()-starttotal),i)
        dmd._pathReindexed = True


RebuildPathIndex()
