##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import Globals
import Queue
import multiprocessing
import sys
import time
import transaction
import traceback
import argparse
import logging
import ctypes
import zope.component
from zExceptions import NotFound
from collections import deque

from OFS.ObjectManager import ObjectManager
from Products.AdvancedQuery import And, Not, MatchGlob, Eq, MatchRegexp, In
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenRelations.ToManyContRelationship import ToManyContRelationship
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.Zuul.catalog.global_catalog import GlobalCatalog
from Products.Zuul.catalog.model_catalog import get_solr_config
from Products.Zuul.utils import dottedname
from zenoss.modelindex.constants import ZENOSS_MODEL_COLLECTION_NAME
from zenoss.modelindex.model_index import IndexUpdate, INDEX, UNINDEX, SearchParams

log = logging.getLogger('zenoss.model_catalog_reindexer')
log.setLevel(logging.INFO)

MODEL_INDEX_BATCH_SIZE = 10000
INDEX_SIZE = 5000


class ReindexProcess(multiprocessing.Process):
    def __init__(self, error_queue, idx, parent_queue, counter, semaphore, cond, cancel):
        super(ReindexProcess, self).__init__()

        self.error_queue = error_queue
        self.idx = idx
        self.parent_queue = parent_queue
        self.counter = counter

        self.semaphore = semaphore
        self.cond = cond
        self.cancel = cancel

        self._batch = []

        self.dmd = ZenScriptBase(connect=True).dmd
        self.index_client = zope.component.createObject('ModelIndex', get_solr_config())

    def get_work(self):
        """
        Returns a uid for the current process to operate on.
        Should be implemented by a subclass.
        """
        raise NotImplementedError

    def batch_update(self, batch, commit=False):
        """
        Uses a Solr index client to perform a batch update of batch.
        """
        self.index_client.process_batched_updates(
            [IndexUpdate(node, op=INDEX) for node in batch],
            commit=commit)

    def index(self, commit=False):
        if self._batch:
            self.batch_update(self._batch, commit)
            self._batch[:] = []

    def handle_exception(self):
        """
        Pass an error to the parent.
        """
        exc = sys.exc_info()
        self.error_queue.put((self.idx, traceback.format_exception(*exc)))
        self.notify_parent()

    def notify_parent(self, wait=False):
        """
	Signal to the parent process that a worker has become idle or has
        encountered an exception.
        """
        with self.cond:
            self.cond.notify_all()
            if wait:
                self.cond.wait(timeout=2)

    def schedule_index(self, node):
        """
        Add a node to the batch. If the batch passes a threshold, index it.
        """
        self._batch.append(node)
        if len(self._batch) >= INDEX_SIZE:
            self.index(True)

    def process(self, uid):
        """
        Process a single uid.
        """
        raise NotImplementedError

    def run(self):
        """
        Operates on uids/nodes from get_work until exhausted.
        """
        count = 0
        while True:
            if self.cancel.is_set():
                return
            with self.semaphore:
                for uid in self.get_work():
                    try:
                        self.process(uid)
                    except Exception:
                        self.handle_exception()
                        continue
                    count += 1
                    # update our counter every so often (less lock usage)
                    if count >= 1000:
                        with self.counter.get_lock():
                            self.counter.value += count
                        count = 0
                        log.debug('Worker {0} notifying parent holding semaphore'.format(self.idx))
                        self.notify_parent()
            # Flush the index batch dregs
            self.index(True)
            if count:
	        with self.counter.get_lock():
	            self.counter.value += count
	        count = 0
            # Should we die? Or wait for more work from the parent?
            if self.cancel.is_set():
                return
            log.debug('Worker {0} notifying parent without holding semaphore'.format(self.idx))
            self.notify_parent(True)

class HardReindex(ReindexProcess):
    """
    A ReindexProcess which uses a tree splitting strategy to share work.

    General flow for a single HardReindex process is:
    If deque is empty, get node from parent queue.
    Else get node from right side of deque.
    Push node's children to right side of deque (if applicable).
    Add node to list of items to be indexed.
    Index all items in list if fit.
    If parent queue is empty, pop a node from left side of deque and push to parent queue.
    Repeat.
    """
    def __init__(self, *args, **kwargs):
        super(HardReindex, self).__init__(*args, **kwargs)
        self.deque = deque()

    def get_work(self):
        while True:
            while self.deque:
                yield self.deque.pop()
            try:
                yield self.parent_queue.get(timeout=2)
            except Queue.Empty:
                pass
            # If we've gotten here and the deque is empty, we have nothing to do
            if not self.deque:
                log.debug("Worker {0} is effectively idle".format(self.idx))
                return

    def process(self, uid):
        try:
            current_node = self.dmd.unrestrictedTraverse(uid)
            self._push_children(current_node)
            if self._include_node(current_node):
                self.schedule_index(current_node)
        finally:
            self._reconcile()

    def _get_children(self, node):
        if isinstance(node, ObjectManager):
            for ob in node.objectValues():
                if isinstance(ob, ZenModelRM):
                    yield ob
                elif isinstance(ob, ToManyContRelationship):
                    for o in ob.objectValuesGen():
                        yield o

    def _push_children(self, node):
        for child in self._get_children(node):
            self.deque.append("/".join(child.getPhysicalPath()))

    def _include_node(self, node):
        return isinstance(node, ZenModelRM) and not isinstance(node, GlobalCatalog)

    def _reconcile(self):
        try:
            if self.parent_queue.empty():
                idle = self.semaphore.get_value() + 1
                log.debug("Worker {0} putting {1} into parent queue. Remaining: {2}".format(self.idx, idle, len(self.deque)))
                for _ in xrange(idle):
		    self.parent_queue.put(self.deque.popleft())
        except IndexError:
            pass


class SoftReindex(ReindexProcess):
    """
    A ReindexProcess which uses a workerpool style strategy to work.

    General flow for a single SoftReindex process is:
    Get node from parent queue.
    Add node to list of items to be indexed.
    Index all items in list if fit.
    Repeat.
    """
    def get_work(self):
        """
        Returns items from the parent queue until signaled to stop.
        """
        while True:
            try:
                yield self.parent_queue.get(timeout=2)
            except Queue.Empty:
                return

    def process(self, uid):
        current_node = self.dmd.unrestrictedTraverse(uid)
        self.schedule_index(current_node)


def get_uids(index_client, root="", types=()):
    start = 0
    need_results = True
    query = [ Eq("tx_state", 0) ]
    query.append(MatchGlob("uid", "{}*".format(root)))

    if not isinstance(types, (tuple, list)):
        types = (types,)

    if types:
        query.append(In("objectImplements", [dottedname(t) for t in types]))

    while need_results:
        search_results = index_client.search(SearchParams(
            query=And(*query),
            start=start,
            limit=MODEL_INDEX_BATCH_SIZE,
            order_by="uid",
            fields=["uid"]))
        start += MODEL_INDEX_BATCH_SIZE
        for result in search_results.results:
            yield result.uid
        need_results = start < search_results.total_count


def init_model_catalog(collection_name=ZENOSS_MODEL_COLLECTION_NAME):
    index_client = zope.component.createObject('ModelIndex', get_solr_config(), collection_name)
    config = {}
    config["collection_name"] = collection_name
    config["collection_config_name"] = collection_name
    config["num_shards"] = 1
    index_client.init(config)
    return index_client


def run(processor_count=8, hard=False):
    log.info("Beginning {0} reindexing with {1} child processes.".format(
    "hard" if hard else "soft", processor_count))
    start = time.time()

    log.info("Initializing model database and Solr model catalog...")
    dmd = ZenScriptBase(connect=True).dmd
    index_client = init_model_catalog()

    processes = []
    error_queue = multiprocessing.Queue()
    parent_queue = multiprocessing.Queue()
    counter = multiprocessing.Value(ctypes.c_uint32)
    semaphore = multiprocessing.Semaphore(processor_count)
    cond = multiprocessing.Condition()
    cancel = multiprocessing.Event()

    processes_remaining = 0
    work = []
    Worker = None

    proc_start = time.time()

    if hard:
        log.info("Clearing Solr data")
        index_client.clear_data()
        work.append("/zport")
        Worker = HardReindex
    else:
        log.info("Reading uids from Solr")
        work = get_uids(index_client)
        Worker = SoftReindex

    log.info("Starting child processes")
    for n in range(processor_count):
        p = Worker(error_queue, n, parent_queue, counter, semaphore, cond, cancel)
        processes.append(p)
        p.start()

    for uid in work:
        parent_queue.put(uid)

    log.info("Waiting for processes to finish")

    lastcount = 0
    last = start
    while True:
        with cond:
            cond.wait()
            try:
                # Print any errors we've built up
                while not error_queue.empty():
                    try:
                        idx, exc = error_queue.get_nowait()
                    except Queue.Empty:
                        pass # This shouldn't happen, but just in case there's a race somehow
                    else:
                        log.error("Indexing process {0} encountered an exception: {1}".format(idx, exc))
                # Print status
                with counter.get_lock():
	            delta = counter.value - lastcount
                    if delta > MODEL_INDEX_BATCH_SIZE:
                        now = time.time()
                        persec = delta/(now - last)
                        last, lastcount = now, counter.value
                        log.info("Indexed {0} objects ({1}/sec)".format(lastcount, persec))
                # Check to see if we're done
                log.debug("{0} workers still busy".format(processor_count - semaphore.get_value()))
                log.debug("parent queue is {0}empty".format("" if parent_queue.empty() else "not "))
                if semaphore.get_value() == processor_count and parent_queue.empty():
                    # All workers are idle and there's no more work to do, so the end
                    log.info("All workers idle, queue empty. Done!")
                    cancel.set()
                    break
            finally:
                # Pass the ball back to the child that notified
                cond.notify_all()
    end = time.time()
    for proc in processes:
        log.debug("Joining proc {0}".format(proc.idx))
        proc.join(5)
        if proc.is_alive():
            proc.terminate()
    log.info("Total time: {0}".format(end - start))
    log.info("Time to initialize: {0}".format(proc_start - start))
    log.info("Time to process and reindex: {0}".format(end - proc_start))
    log.info("Number of objects indexed: {0}".format(counter.value))


def reindex_model_catalog(dmd, root="/zport", idxs=None, types=()):
    """
    Performs a single threaded soft reindex
    """
    start = time.time()
    log.info("Performing soft reindex on model_catalog. Params = root:'{}' / idxs:'{}' / types:'{}'".format(root, idxs, types))
    modelindex = init_model_catalog()
    uids = get_uids(modelindex, root=root, types=types)
    if uids:
        index_updates = []
        for uid in uids:
            try:
                obj = dmd.unrestrictedTraverse(uid)
            except (KeyError, NotFound):
                log.warn("Stale object found in Solr: {}".format(uid))
                index_updates.append(IndexUpdate(None, op=UNINDEX, uid=uid))
            else:
                index_updates.append(IndexUpdate(obj, op=INDEX, idxs=idxs))
            if len(index_updates) % 1000 == 0:
                modelindex.process_batched_updates(index_updates, commit=False)
                index_updates = []
        if index_updates:
            modelindex.process_batched_updates(index_updates, commit=True)
        else:
            modelindex.commit()
    log.info("Reindexing took {} seconds.".format(time.time()-start))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reindex Solr against ZODB.")
    parser.add_argument("-f", "--hard", action="store_true",
                        help="wipe Solr data and traverse the entire ZODB tree")
    parser.add_argument("-p", "--procs", type=int, default=8,
                        help="use n child processes (default 8)")
    args = parser.parse_args()
    # Something else seems to want to parse our args, so reset them
    sys.argv = sys.argv[:1]
    run(args.procs, args.hard)
