##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import sys
import time
import Migrate
import zExceptions

import logging
log = logging.getLogger('zen.migrate')

from Products.AdvancedQuery import In
from Products.Zuul.interfaces import ICatalogTool
from Products.ZCatalog.Catalog import CatalogError
from Products.ZenUtils.Search import makeCaseInsensitiveKeywordIndex

class MacAddressIndex(Migrate.Step):
    version = Migrate.Version(4, 9, 70)

    def cutover(self, dmd):
        cat = dmd.zport.global_catalog

        try:
            cat.addIndex('macAddresses',
                makeCaseInsensitiveKeywordIndex('macAddresses'))

            if hasattr(cat, 'applyConfig'):
                cat.applyConfig()

            print "Reindexing.  This may take some time..."
            starttotal = time.time()
            tstart = time.time()
            i = 0
            CHUNK_SIZE = 200 if sys.stdout.isatty() else 25000 # Don't be chatty when logging to file

            fqdns = ('Products.ZenModel.IpInterface.IpInterface',
                     'ZenPacks.zenoss.ZenVMware.VMwareGuest.VMwareGuest',
                     'ZenPacks.zenoss.vCloud.VM.VM',)
            results = ICatalogTool(dmd).search(fqdns)

            for result in results.results:
                i+=1
                try:
                    result.getObject().index_object()
                except TypeError:
                    # work around for bad data
                    log.warning("Unable to index %s" % result.getPath())
                except (KeyError, zExceptions.NotFound):
                    cat.uncatalog_object(result.getPath())

                if i % CHUNK_SIZE == 0:
                    self.log_progress("rate=%.2f/sec count=%d of %d" % 
                        (CHUNK_SIZE/(time.time() - tstart), i, results.total))
                    tstart = time.time()
            print
            log.info("Finished total time=%.2f rate=%.2f count=%d",
                time.time()-starttotal, i/(time.time()-starttotal), i)
        
        except CatalogError:
            pass

MacAddressIndex()

