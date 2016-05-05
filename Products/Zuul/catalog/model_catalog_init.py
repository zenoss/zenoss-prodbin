
import Globals
from Products.ZenUtils.ZenScriptBase import ZenScriptBase

import multiprocessing
import signal
import sys
import time
import transaction
import traceback
import zope.component

from OFS.ObjectManager import ObjectManager
from Products.AdvancedQuery import And, Not, MatchGlob
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenRelations.ToManyContRelationship import ToManyContRelationship
from Products.Zuul.catalog.global_catalog import GlobalCatalog
from Products.Zuul.catalog.model_catalog import get_solr_config
from zenoss.modelindex.constants import ZENOSS_MODEL_COLLECTION_NAME
from zenoss.modelindex.model_index import IndexUpdate, INDEX, UNINDEX, SearchParams
from zenoss.modelindex.solr.solr_client import SolrClient

import logging

log = logging.getLogger('zenoss.model_catalog_reindexer')
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler(sys.stdout))


DEFAULT_BATCH_SIZE = 10000


class BatchResult(object):
    def __init__(self, more_objects, processed_objects):
        self.more_objects = more_objects
        self.processed_objects = processed_objects


class BatchProcessor(object):

    def __init__(self, indexer=None, batch_size=DEFAULT_BATCH_SIZE):
        self.BATCH_SIZE = batch_size
        self.indexer = indexer
        if not self.indexer:
            self.indexer = zope.component.createObject('ModelIndex', get_solr_config())

    def _send_batch(self, batch, commit=False):
        if batch:
            ts = time.time()
            self.indexer.process_batched_updates(batch, commit=commit)
            log_text = "{0} - Sending {1} docs took {2} seconds. Commit = {3}"
            log.debug(log_text.format(multiprocessing.current_process(), len(batch), time.time() - ts, commit))

    def process_batch(self, object_generator, idxs=None):
        batch = []
        more_objects = True
        processed_objects = 0
        while processed_objects < self.BATCH_SIZE:
            try:
                obj = next(object_generator)
                processed_objects = processed_objects + 1
                batch.append(IndexUpdate(obj, op=INDEX, idxs=idxs))
            except StopIteration:
                more_objects = False
                break
        commit = not more_objects
        self._send_batch(batch, commit=commit)
        #self._send_batch(batch, commit=False)
        del batch
        return BatchResult(more_objects, processed_objects)


class RecursiveDefaultDict(dict):
    def __missing__(self, key):
        self[key] = RecursiveDefaultDict()
        return self[key]


class CatalogableObjectsRetriever(object):
    """ Base class for object retriever """
    def __init__(self, start_path, exclude_paths=None):
        self.dmd = ZenScriptBase(connect=True).dmd # get a connection to zodb
        self.start_path = start_path
        self.exclude_paths = None
        if exclude_paths:
            self.exclude_paths = exclude_paths
            if not isinstance(exclude_paths, set):
                self.exclude_paths = set(exclude_paths)

    def _is_excluded(self, obj_path):
        exclude_obj = True
        if obj_path:
            if obj_path.startswith(self.start_path):
                if self.exclude_paths:
                    exclude_obj = any(obj_path.startswith(x) for x in self.exclude_paths)
                else:
                    exclude_obj = False
        return exclude_obj

    def get_catalogable_objects(self):
        raise NotImplementedError


class ZodbObjectsRetriever(CatalogableObjectsRetriever):

    def __init__(self, start_path, exclude_paths=None):
        super(ZodbObjectsRetriever, self).__init__(start_path, exclude_paths)
        self.root = self.dmd.unrestrictedTraverse(start_path)

    def _find_kids(self, obj, call_tree):
        nones_counted = 0
        for kid in self._recurse(obj, call_tree):
            if kid is None:
                nones_counted += 1
            else:
                yield kid
        if nones_counted:
            try:
                description = obj.getPrimaryPath()
            except Exception:
                description = repr(obj)
            log.error("Object %s has a None child!" % description)

    def _recurse(self, obj, call_tree=None):
        if call_tree is None:
            call_tree = RecursiveDefaultDict()
        while True:
            obj_id = obj.id
            try:
                tree = call_tree[obj_id]
                if tree is not False:
                    if not isinstance(obj, GlobalCatalog):
                        obj_path = "/".join(obj.getPhysicalPath())
                        if self._is_excluded(obj_path):
                            call_tree[obj_id] = False
                            continue
                        if isinstance(obj, ObjectManager):
                            for ob in obj.objectValues():
                                for kid in self._find_kids(ob, tree):
                                    yield kid
                            if isinstance(obj, ZenModelRM):
                                for rel in obj.getRelationships():
                                    if isinstance(rel, ToManyContRelationship):
                                        for kid in self._find_kids(rel, tree):
                                            yield kid
                                yield obj
                        elif isinstance(obj, ToManyContRelationship):
                            for ob in obj.objectValuesGen():
                                for kid in self._find_kids(ob, tree):
                                    yield kid
                    # invalidation allows object to be garbage collected
                    inv = getattr(obj, '_p_invalidate', None)
                    if inv is not None: inv()
                    call_tree[obj_id] = False
            except AttributeError as e:
                log.exception('Error in cataloging {0} / {1}'.format(obj, e))
            break

    def get_catalogable_objects(self):
        call_tree = RecursiveDefaultDict()
        for obj in self._recurse(self.root, call_tree):
            yield obj

    def get_catalogable_objects_count(self):
        call_tree = RecursiveDefaultDict()
        count = 0
        for obj in self._recurse(self.root, call_tree):
            count = count + 1
        return count


class ModelIndexObjectsRetriever(CatalogableObjectsRetriever):
    """ Retrieves Zenoss Catalogable Objects using model_index as source """

    def __init__(self, start_path, exclude_paths=None):
        super(ModelIndexObjectsRetriever, self).__init__(start_path, exclude_paths)
        self.model_index = zope.component.createObject('ModelIndex', get_solr_config())

    def get_catalogable_objects(self, search_batch_size=DEFAULT_BATCH_SIZE):
        """ """
        more_objects = True
        start = 0
        query = MatchGlob("uid", "{0}*".format(self.start_path))
        if self.exclude_paths:
            query_terms = [ query ]
            for ep in self.exclude_paths:
                exclude_term = Not( MatchGlob("uid", "{0}*".format(ep)) )
                query_terms.append(exclude_term)
            query = And( *query_terms )

        search_params = SearchParams(query, start=start, limit=search_batch_size, fields=["uid"])
        while more_objects:
            ts = time.time()
            search_params.start = start
            search_results = self.model_index.search(search_params)
            log.info("search batch [ {0} / {1} ] took {2} seconfs".format(start, search_batch_size, time.time()-ts))
            for brain in search_results.results:
                try:
                    obj = self.dmd.unrestrictedTraverse(str(brain.uid))
                except Exception as e:
                    log.warn("Error retrieving object {0} from zodb".format(brain.uid))
                else:
                    yield obj
            start = start + search_batch_size
            more_objects = start <= search_results.total_count


class ModelCatalogReindexer(object):

    def __init__(self, object_retriever):
        self.object_retriever = object_retriever
        self.indexer = zope.component.createObject('ModelIndex', get_solr_config())

    def _process_batch(self, object_generator, idxs, batch_size):
        batch_processor = BatchProcessor(self.indexer, batch_size)
        more_objects = batch_processor.process_batch(object_generator, idxs)
        del batch_processor
        return more_objects

    def reindex(self, idxs, batch_size=DEFAULT_BATCH_SIZE):
        """ """
        object_generator = self.object_retriever.get_catalogable_objects()

        start = time.time()
        more_objects = True
        object_count = 0
        while more_objects:
            ts = time.time()
            batch_result = self._process_batch(object_generator, idxs, batch_size)
            more_objects = batch_result.more_objects
            object_count = object_count + batch_result.processed_objects
            if more_objects: # Report status for workers with big tasks
                log_text = "{0} - Processing batch of {1} docs took {2} seconds. Root path = {3}"
                log.info(log_text.format(multiprocessing.current_process(), batch_size, time.time() - ts, self.object_retriever.start_path))
            transaction.abort()
        log.info("Reindexing {0} objects took {1} seconds.".format(object_count, time.time() - start))

from MySQLdb import ProgrammingError

def reindex_tree(task, hard=True, batch_size=DEFAULT_BATCH_SIZE):
    """
        @param task: ReindexTask
        @param hard: if true get objects to index from zodb else get them from model_index
    """
    try:
        start = time.time()
        log_text = "Assigning thread {0} to reindex tree {1}"
        log.info(log_text.format(multiprocessing.current_process(), task.start_path))
        if hard:
            object_retriever = ZodbObjectsRetriever(task.start_path, task.exclude_paths)
        else:
            object_retriever = ModelIndexObjectsRetriever(task.start_path, task.exclude_paths)
        reindexer = ModelCatalogReindexer(object_retriever)
        reindexer.reindex(task.idxs, batch_size)
        log_text = "Thread {0} finished reindexing tree {1} in {2} seconds."
        log.info(log_text.format(multiprocessing.current_process(), task.start_path, time.time() - start))
    except ProgrammingError as pe:
        log.info("\n{0} Got ProgrammingError exception\n".format(multiprocessing.current_process()))
    except Exception as e:
        print "EXCEPTION IN CHILD {0}".format(traceback.print_exc())
        raise e


def reindex_slow(idxs=None, hard=True):
    """ single process reindex """
    start = time.time()
    reindex_tree(ReindexTask("/zport", idxs=idxs), hard=hard)
    log.info("Total Execution time: {0} seconds".format(time.time()-start))


'''
class ReindexWorker(multiprocessing.Process):
    def __init__(self, task_queue, result_queue=None):
        multiprocessing.Process.__init__(self)
        self.task_queue = task_queue
        self.result_queue = result_queue

    def _run(self, hard, batch_size):
        try:
            done = False
            task = self.task_queue.get()
            if task is None:
                print '%s: Exiting' % self.name
                done = True
            else:
                # do work
                print "{0}: Working".format(self.name)
                reindex_tree(task, hard, batch_size)
                #self.do_work(task)
                done = False
            self.task_queue.task_done()
        except KeyboardInterrupt as e:
            raise e
        except Exception:
            print traceback.print_exc()
            done = True

        return done

    def run(self, hard=True, batch_size=DEFAULT_BATCH_SIZE):
        try:
            done = False
            while not done:
                done = self._run(hard, batch_size)
        except KeyboardInterrupt:
            print "{0} AMONOS".format(self.name)


def reindex_2(dmd, idxs=None, hard=True, n_workers=4):
    # NEW IMPL
    if n_workers <= 1:
        return reindex_slow(idxs, hard)

    start = time.time()
    tasks_queue = multiprocessing.JoinableQueue()

    workers = [ ReindexWorker(tasks_queue) for i in xrange(n_workers) ]

    for w in workers:
        w.start()

    for task in get_worker_tasks(dmd, idxs):
        tasks_queue.put(task)

    # poison pill
    for i in xrange(n_workers):
        tasks_queue.put(None)

    tasks_queue.join()
    log.info("Total Execution time: {0} seconds".format(time.time()-start))
'''


def reindex(dmd, idxs=None, hard=True, n_workers=4):
    """ reindex using a pool of workers """
    if n_workers <= 1:
        return reindex_slow(idxs, hard)

    start = time.time()
    worker_tasks = get_worker_tasks(dmd, idxs)

    # This is needed. Otherwise the workers won't get the ctlr-c signal
    original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    pool = multiprocessing.Pool(n_workers)
    signal.signal(signal.SIGINT, original_sigint_handler)
    try:
        total_tasks = len(worker_tasks)
        pending_tasks = total_tasks
        log.info("Sending {0} reindex tasks to {1} workers...".format(total_tasks, n_workers))
        res = pool.map_async(reindex_tree, worker_tasks, chunksize=1)
        while True:
            try:
                time.sleep(60)
                res.get(10)
            except multiprocessing.TimeoutError:
                if res._number_left != pending_tasks:
                    log.info("Completed {0} out of {1} indexing tasks".format(total_tasks - res._number_left, total_tasks))
                    pending_tasks = res._number_left
            else:
                break

    except KeyboardInterrupt:
        log.warn("Reindex interrupted. This may leave Zenoss in an inconsistent state.")
        pool.terminate()
    except Exception as e:
        log.warn("Exception while reindexing. This may leave Zenoss in an inconsistent state. /{0}/{1}/".format(e.message, type(e)))
        print traceback.print_exc()
        pool.terminate()
    else:
        pool.close()
        log.info("Total Execution time: {0} seconds".format(time.time()-start))
    pool.join()


class ReindexTask(object):

    def __init__(self, start, exclude=None, idxs=None):
        self.start_path = start
        self.exclude_paths = exclude if exclude else set()
        self.idxs = idxs
        if self.exclude_paths:
            if isinstance(self.exclude_paths, basestring):
                self.exclude_paths = set()
                self.exclude_paths.add(exclude)
            elif not isinstance(self.exclude_paths, set):
                self.exclude_paths = set(self.exclude_paths)

    def __str__(self):
        return "start_path: {0} / exclude_paths: {1}".format(self.start_path, self.exclude_paths)

def get_task_stats():
    total_count = 0
    tasks = get_worker_tasks()
    for t in tasks:
        object_retriever = ZodbObjectsRetriever(t.start_path, t.exclude_paths)
        count = object_retriever.get_catalogable_objects_count()
        log.info("Task: {0} \n\tCount: {1}".format(t, count))
        total_count = total_count + count
    log.info("Total Number of objects: {0}".format(total_count))


def get_worker_tasks(dmd, idxs=None):
    """ @TODO make this smarter """
    tasks = []
    top_level_excludes = [] # path that the taks to reindex zport needs to exclude

    """ Tasks to reindex Device Classes """
    # a task per device class
    device_classes_root_path = dmd.Devices.getPrimaryId()
    # device_classes_paths = [ "{0}{1}".format(device_classes_root_path, dc).rstrip('/') for dc in dmd.Devices.getPeerDeviceClassNames() ]
    device_classes_paths = [ dc.getPrimaryId() for dc in dmd.Devices.children() ]
    for dc_path in device_classes_paths:
        tasks.append(ReindexTask(dc_path, idxs=idxs))
    # a task for the device class root
    tasks.append(ReindexTask(device_classes_root_path, device_classes_paths, idxs=idxs))
    top_level_excludes.append(device_classes_root_path)

    """ Tasks to reindex trees under zport.dmd """
    trees = []
    trees.append(dmd.ZenUsers)
    trees.append(dmd.Processes)
    trees.append(dmd.Services)
    trees.append(dmd.Mibs)
    trees.append(dmd.Reports)
    trees.append(dmd.IPv6Networks)
    trees.append(dmd.Networks)

    for root_node in trees:
        root_path = root_node.getPrimaryId()
        tasks.append(ReindexTask(root_path, idxs=idxs))
        top_level_excludes.append(root_path)

    # @TODO think how to make Networks and Devices reindex faster

    # add zport excluding network roots paths and device classes root path
    dmd_task = ReindexTask("/zport/dmd", top_level_excludes, idxs=idxs)
    tasks.append(dmd_task)
    zport_task = ReindexTask("/zport", "/zport/dmd", idxs=idxs)
    tasks.append(zport_task)
    tasks.reverse()
    return tasks


def soft_reindex(dmd, idxs=None, n_workers=8):
    """ Reindex using solr as source """
    reindex(dmd, idxs, hard=False, n_workers=n_workers )


def hard_reindex(dmd, idxs=None, n_workers=8):
    """ Reindex using zodb as source """
    log.info("Clearing Model Catalog data...")
    clear_data()
    log.info("Preparing to reindex....")
    reindex(dmd, idxs, hard=True, n_workers=n_workers )


def init_model_catalog(collection_name=ZENOSS_MODEL_COLLECTION_NAME):
    model_index = zope.component.createObject('ModelIndex', get_solr_config(), collection_name)
    config = {} # @TODO we should read config values from file
    config["collection_name"] = collection_name
    config["num_shards"] = 1
    model_index.init(config)


def clear_data(collection_name=ZENOSS_MODEL_COLLECTION_NAME):
    solr_config = get_solr_config()
    model_index = zope.component.createObject('ModelIndex', solr_config)
    model_index.clear_data()


def init(dmd):
    init_model_catalog()
    hard_reindex(dmd)


if __name__ == "__main__":
    dmd = ZenScriptBase(connect=True).dmd
    init(dmd)


#----------------------------------------------------
#         Tools for memory usage investigation
#----------------------------------------------------
#
# Memory profiler:
#
#     from memory_profiler import profile
#     add @profile decorator to each method we want to profile
#     
# Force garbage collection
#     import gc
#     collected = gc.collect()
#     
# Get object references graph:
#     
#     import objgraph
#     
#     - get objects in heap by type:  objgraph.by_type("IpAddress")
#     - get object count:  objgraph.count('IpNetwork')
#     - other useful methods
#            objgraph.most_common_types(limit=50)
#            objgraph.show_most_common_types(limit=50)
#            objgraph.show_growth(limit=50)
#            objgraph.get_leaking_objects()
#     - generate graph with references from/to a specific objects
#            objgraph.show_backrefs([obj], max_depth=5, too_many=20, filename="/opt/zenoss/Products/objgraph_rev.dot", refcounts=True)
#            objgraph.show_refs([obj], max_depth=5, too_many=20, filename="/opt/zenoss/Products/objgraph.dot", refcounts=True)
#               - convert dot to png:
#                   import pydot
#                   dot_file="objgraph_rev.dot"
#                   graph = pydot.graph_from_dot_file(dot_file)
#                   graph.write_png('mem.png')
#
# Get reference count of object
#           import sys
#           sys.getrefcount(net)
#
# Explore heap
#     - before code we want to measure
#           from guppy import hpy
#           hp = hpy()
#           before = hp.heap()
#     - after code we want to measure
#           after = hp.heap()
#           leftover = after - before
#           byrcs = leftover.byrcs
#
#






