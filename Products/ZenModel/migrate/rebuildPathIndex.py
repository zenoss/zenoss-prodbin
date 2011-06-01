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
import Migrate
import zExceptions

import logging
log = logging.getLogger("zen.migrate")

import time

class RebuildPathIndex(Migrate.Step):
    version = Migrate.Version(3, 1, 70)

    def cutover(self, dmd):
        if getattr(dmd, "_pathReindexed", None) is not None:
            log.info('path has already been reindexed')
            return
        zport = dmd.getPhysicalRoot().zport
        tstart=time.time()
        starttotal = time.time()
        i = 0
        # device Search
        for x in dmd.Devices.deviceSearch():
            try:
                x.getObject().index_object(idxs=('path',))
            except TypeError:
                # for upgrade the zenpacks may not have loaded the new code yet
                x.getObject().index_object()
        # global catalog
        for x in zport.global_catalog():
            i+=1
            try:
                zport.global_catalog.catalog_object(x.getObject(),x.getPath(),
                                                    idxs=['path'],
                                                    update_metadata=False)
            except TypeError:
                # work around for bad data
                log.warning("Unable to index %s " % x.getPath())
            except (KeyError, zExceptions.NotFound):
                zport.global_catalog.uncatalog_object(x.getPath())
            if i % 200 == 0:
                log.info("rate=%.2f/sec count=%d", 200/(time.time()-tstart), i)
                tstart=time.time()
        log.info("Finished total time=%.2f rate=%.2f count=%d",
                time.time()-starttotal, i/(time.time()-starttotal),i)
        dmd._pathReindexed = True


RebuildPathIndex()
