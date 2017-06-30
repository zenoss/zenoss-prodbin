##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

import logging
import signal
import sys

from Globals import *

from multiprocessing import Process
from Products.ZenUtils.ZenDaemon import ZenDaemon
from Products.Zuul.catalog.model_catalog_init import run as run_model_catalog_init
from Products.Zuul.catalog.model_catalog_init import collection_exists

log = logging.getLogger("zen.Catalog")

# Hide connection errors. We handle them all ourselves.
HIGHER_THAN_CRITICAL = 100
logging.getLogger('ZODB.Connection').setLevel(HIGHER_THAN_CRITICAL)
logging.getLogger('ZEO.zrpc').setLevel(HIGHER_THAN_CRITICAL)


class CatalogReindexAborted(Exception): pass

def raiseKeyboardInterrupt(signum, frame):
    raise KeyboardInterrupt()

def ignore_interruptions():
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    signal.signal(signal.SIGUSR2, signal.SIG_IGN)

def drop_all_arguments():
    sys.argv[:] = sys.argv[:1]

def _run_model_catalog_init(worker_count, hard, idxs):
    ignore_interruptions()
    drop_all_arguments()
    run_model_catalog_init(worker_count, hard, indexes=idxs)


# Note: We are very careful not to connect to the database nor memcache until
# *after* we have finished forking new processes. The MySQL and Memcache client
# libraries both require each fork to have its own object handles. That's why
# we extend ZenDaemon, instead of ZCmdBase)
class ZenCatalogBase(ZenDaemon):
    name = 'zencatalog'

    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZenDaemon.buildOptions(self)
        self.parser.add_option("--createcatalog",
                               action="store_true",
                               default=False,
                               help="Create global catalog and populate it")
        self.parser.add_option("--forceindex",
                               action="store_true",
                               default=False,
                               help="works with --createcatalog to re-create index, "
                                    "if catalog exists it will be dropped first")
        self.parser.add_option("--reindex",
                               action="store_true",
                               default=False,
                               help="reindex existing catalog")
        self.parser.add_option("--permissionsOnly",
                               action="store_true",
                               default=False,
                               help="Only works with --reindex, only update " \
                                    " permissions")
        self.parser.add_option("--resume",
                               action="store_true",
                               default=False,
                               help="DEPRECATED")
        self.parser.add_option("--clearmemcached",
                               action="store_true",
                               default=False,
                               help="clears memcached after processing")
        self.parser.add_option("--workers",
                               type="int",
                               default=8,
                               help="Number of processes working simultaneously")
        self.parser.add_option("--buffersize",
                               type="int",
                               default=200,
                               help="DEPRECATED")
        self.parser.add_option("--inputqueuesize",
                               type="int",
                               default=300,
                               help="DEPRECATED")
        self.parser.add_option("--processedqueuesize",
                               type="int",
                               default=300,
                               help="DEPRECATED")

    def run(self):
        print_progress = not self.options.daemon
        if self.options.createcatalog:
            return self._create_catalog(
                worker_count=self.options.workers,
                buffer_size=self.options.buffersize,
                input_queue_size=self.options.inputqueuesize,
                processed_queue_size=self.options.processedqueuesize,
                force=self.options.forceindex,
                clearmemcached=self.options.clearmemcached,
                resume=self.options.resume,
                print_progress=print_progress)
        elif self.options.reindex:
            return self._reindex(
                worker_count=self.options.workers,
                buffer_size=self.options.buffersize,
                input_queue_size=self.options.inputqueuesize,
                processed_queue_size=self.options.processedqueuesize,
                permissions_only=self.options.permissionsOnly,
                resume=self.options.resume,
                print_progress=print_progress)
        else:
            self.parser.error("Must use one of --createcatalog, --reindex")
            return False

    def _process(self, worker_count, hard, permissions_only=False):
        idxs = ["allowedRolesAndUsers"] if permissions_only else []
        p = Process(
            target=_run_model_catalog_init,
            args=(worker_count, hard, idxs)
        )
        try:
            p.start()
            p.join()
        except KeyboardInterrupt:
            log.info("Received signal to terminate, terminating subprocess")
            p.terminate()

    def _create_catalog(self, worker_count, buffer_size, input_queue_size, processed_queue_size, force=False, clearmemcached=False, resume=True, print_progress=True):
        if resume:
            log.info("--resume is deprecated.  Performing a full index")
        if not force:
            if self._check_for_global_catalog():
                log.info("Global catalog already exists. " \
                         "Run with --forceindex to drop and recreate catalog.")
                return False

        log.info("Recataloging your system. This may take some time.")

        self._process(worker_count=worker_count, hard=True)

        if clearmemcached:
            import memcache
            servers = self.options.zodb_cacheservers.split()
            try:
                log.info("Flushing memcache servers: %r" % servers)
                mc = memcache.Client(servers)
                mc.flush_all()
                mc.disconnect_all()
            except Exception as ex:
                log.error("problem flushing cache server %r: %r" % (servers, ex))
        return True

    def _reindex(self, worker_count, buffer_size, input_queue_size, processed_queue_size, permissions_only=False, resume=True,  print_progress=True):
        if not self._check_for_global_catalog():
            msg = 'Global Catalog does not exist, try --createcatalog option'
            log.warning(msg)
            return False

        log.info("Reindexing your system. This may take some time.")

        self._process(worker_count=worker_count, hard=False, permissions_only=permissions_only)

        return True

    def _check_for_global_catalog(self):
        return collection_exists()

if __name__ == "__main__":
    zc = ZenCatalogBase()
    try:
        # signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, raiseKeyboardInterrupt)
        signal.signal(signal.SIGUSR2, signal.SIG_IGN)
        zc.run()
    except Exception:
        log.exception("Failed!")
