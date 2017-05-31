import Globals
import Queue
import multiprocessing
import sys
import time
import transaction
import traceback
import argparse
import logging
import zope.component
from collections import deque

from OFS.ObjectManager import ObjectManager
from Products.AdvancedQuery import And, Not, MatchGlob, Eq, MatchRegexp
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenRelations.ToManyContRelationship import ToManyContRelationship
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.Zuul.catalog.global_catalog import GlobalCatalog
from Products.Zuul.catalog.model_catalog import get_solr_config
from zenoss.modelindex.constants import ZENOSS_MODEL_COLLECTION_NAME
from zenoss.modelindex.model_index import IndexUpdate, INDEX, SearchParams

log = logging.getLogger('zenoss.model_catalog_reindexer')
log.setLevel(logging.INFO)

MODEL_INDEX_BATCH_SIZE = 10000
INDEX_SIZE = 5000

class WorkerReport(object):
    def __init__(self, idx, count, err=None):
        self.idx = idx
        self.count = count
        self.err = err


class ReindexProcess(multiprocessing.Process):
    def __init__(self, queue, idx, parent_queue):
        super(ReindexProcess, self).__init__()

        self.queue = queue
        self.idx = idx
        self.parent_queue = parent_queue

        self.dmd = ZenScriptBase(connect=True).dmd
        self.index_client = zope.component.createObject('ModelIndex', get_solr_config())

    def get_work(self):
        """
        Returns a uid for the current process to operate on.
        Should be implemented by a subclass.
        """
        raise NotImplementedError

    def push_children(self, node):
        """
        Puts the children of node in an appropriate queue.
        Should be implemented by a subclass.
        """
        raise NotImplementedError

    def include_node(self, node):
        """
        Returns whether or not to include the node in a batch to be indexed.
        Should be implemented by a subclass.
        """
        raise NotImplementedError

    def batch_update(self, batch, commit=False):
        """
        Uses a solr index client to perform a batch update of batch.
        """
        self.index_client.process_batched_updates(
            [IndexUpdate(node, op=INDEX) for node in batch],
            commit=commit)

    def index(self, batch, commit=False):
        """
        Wraps batch_update to perform other necessary tasks.
        Should be implemented by a subclass.
        """
        raise NotImplementedError

    def reconcile(self):
        """
        Reconciles queues or other properties after operating on a node.
        Should be implemented by a subclass.
        """
        raise NotImplementedError

    def do_work(self):
        """
        Operates on uids/nodes from get_work until exhausted.
        """
        count = 0
        batch = []

        try:
            for current_uid in self.get_work():
                current_node = self.dmd.unrestrictedTraverse(current_uid)
                self.push_children(current_node)
                if self.include_node(current_node):
                    batch.append(current_node)
                    count += 1
                    if count % INDEX_SIZE == 0:
                        self.index(batch)
                        batch = []
                self.reconcile()
            # Mandatory to commit before we bail
            self.index(batch, True)
            return WorkerReport(self.idx, count)
        except Queue.Empty:
            # The parent_queue is empty, which means we're done
            self.index(batch, True)
            return WorkerReport(self.idx, count)
        except Exception as e:
            # grab the traceback for the report
            return WorkerReport(self.idx, count - len(batch), traceback.format_exc())

    def run(self):
        self.queue.put(self.do_work())


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
    def __init__(self, queue, idx, parent_queue):
        super(HardReindex, self).__init__(queue, idx, parent_queue)
        self.deque = deque()

    def get_work(self):
        yield self.parent_queue.get(timeout=30)
        while True:
            try:
                yield self.deque.pop()
            except IndexError:
                yield self.parent_queue.get(timeout=2)

    def push_children(self, node):
        if self._include_children(node):
            prefix = "/".join(node.getPhysicalPath()) + "/"
            [self.deque.append(prefix + child) for child in node.objectIds()]

    def _include_children(self, node):
        include = False
        if not isinstance(node, GlobalCatalog):
            if isinstance(node, ObjectManager):
                include = True
            elif isinstance(node, ToManyContRelationship):
                include = True
        return include

    def include_node(self, node):
        include = False
        if not isinstance(node, GlobalCatalog):
            if isinstance(node,ZenModelRM):
                include = True
        return include

    def index(self, batch, commit=False):
        self.batch_update(batch, commit)

    def reconcile(self):
        try:
            if self.parent_queue.empty():
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
    def __init__(self, queue, idx, parent_queue):
        super(SoftReindex, self).__init__(queue, idx, parent_queue)

    def get_work(self):
        yield self.parent_queue.get(timeout=30)
        while True:
            yield self.parent_queue.get(timeout=2)

    def push_children(self, node):
        pass

    def include_node(self, node):
        return True

    def index(self, batch, commit=True):
        self.batch_update(batch, commit)
        transaction.abort()

    def reconcile(self):
        pass

def get_uids(collection_name=ZENOSS_MODEL_COLLECTION_NAME):
    start = 0
    index_client = zope.component.createObject('ModelIndex', get_solr_config(), collection_name)
    need_results = True

    while need_results:
        search_results = index_client.search(SearchParams(
            query=And(MatchGlob("uid", "*"), Eq("tx_state", 0)),
            start=start,
            limit=MODEL_INDEX_BATCH_SIZE,
            fields=["uid"]))
        start += MODEL_INDEX_BATCH_SIZE
        for result in search_results.results:
            yield result
        need_results = start < search_results.total_count

def clear_data(collection_name=ZENOSS_MODEL_COLLECTION_NAME):
    model_index = zope.component.createObject('ModelIndex', get_solr_config(), collection_name)
    model_index.clear_data()

def init_model_catalog(collection_name=ZENOSS_MODEL_COLLECTION_NAME):
    model_index = zope.component.createObject('ModelIndex', get_solr_config(), collection_name)
    config = {}
    config["collection_name"] = collection_name
    config["collection_config_name"] = collection_name
    config["num_shards"] = 1
    model_index.init(config)

def run(processor_count=8, hard=False):
    log.info("Beginning {0} redindexing with {1} child processes.".format(
    "hard" if hard else "soft", processor_count))
    start = time.time()

    log.info("Initializing dmd and solr model catalog...")
    dmd = ZenScriptBase(connect=True).dmd
    init_model_catalog()

    processes = []
    processor_queue = multiprocessing.Queue()
    parent_queue = multiprocessing.Queue()

    processes_remaining = 0
    work = []
    Worker = None

    proc_start = time.time()

    if hard:
        log.info("Clearing solr data")
        clear_data()
        work.append("/zport")
        Worker = HardReindex
    else:
        log.info("Reading uids from solr")
        uids = [brain.uid for brain in get_uids()]
        uids.sort()
        work = uids
        Worker = SoftReindex

    log.info("Starting child processes")
    for n in range(processor_count):
        p = Worker(processor_queue, n, parent_queue)
        processes.append(p)
        p.start()
        processes_remaining += 1

    [parent_queue.put(uid) for uid in work]

    log.info("Waiting for processes to finish")
    total_count = 0

    while processes_remaining > 0:
        proc_report = processor_queue.get()
        if proc_report.err:
            log.error("Process with idx '{0}' exited early with an error".format(proc_report.idx))
            log.exception(proc_report.err)
        log.info("Process with idx '{0}' finished after processing {1} objects.".format(proc_report.idx, proc_report.count))
        processes[proc_report.idx].join()
        processes_remaining -= 1
        total_count += proc_report.count

    end = time.time()

    log.info("Total time: {0}".format(end - start))
    log.info("Time to initialize: {0}".format(proc_start - start))
    log.info("Time to process and reindex: {0}".format(end - proc_start))
    log.info("Number of objects indexed: {0}".format(total_count))

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
