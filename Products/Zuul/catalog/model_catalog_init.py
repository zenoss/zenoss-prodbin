
import Globals
from Products.ZenUtils.ZenScriptBase import ZenScriptBase

import multiprocessing
import time
import transaction
import zope.component

from OFS.ObjectManager import ObjectManager
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenRelations.ToManyContRelationship import ToManyContRelationship
from Products.Zuul.catalog.global_catalog import GlobalCatalog
from Products.Zuul.catalog.model_catalog import get_solr_config
from zenoss.modelindex.constants import ZENOSS_MODEL_COLLECTION_NAME
from zenoss.modelindex.indexer import ModelUpdate, INDEX, UNINDEX
from zenoss.modelindex.solr.solr_client import SolrClient

import logging
import sys

log = logging.getLogger('zenoss.model_catalog_reindexer')
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler(sys.stdout))


DEFAULT_BATCH_SIZE = 10000


class RecursiveDefaultDict(dict):
    def __missing__(self, key):
        self[key] = RecursiveDefaultDict()
        return self[key]


class CatalogableObjectsRetriever(object):

    def __init__(self):
        self.exclude_paths = None

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

    def _is_excluded(self, obj):
        exclude_obj = False
        if obj and self.exclude_paths:
            try:
                ppath = "/".join(obj.getPrimaryPath())
            except:
                pass
            else:
                exclude_obj = len(filter(lambda x: ppath.startswith(x), self.exclude_paths)) > 0
        return exclude_obj

    def _recurse(self, obj, call_tree=None):
        if call_tree is None:
            call_tree = RecursiveDefaultDict()
        while True:
            obj_id = obj.id
            try:
                tree = call_tree[obj_id]
                if tree is not False:
                    if not isinstance(obj, GlobalCatalog):
                        if self._is_excluded(obj):
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

    def get_catalogable_objects(self, root, exclude_paths=None):
        """ """
        if exclude_paths:
            self.exclude_paths = exclude_paths
            if not isinstance(exclude_paths, set):
                self.exclude_paths = set(exclude_paths)

        call_tree = RecursiveDefaultDict()
        for obj in self._recurse(root, call_tree):
            yield obj


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
            self.indexer.process_model_updates(batch, commit=commit)
            log_text = "{0} - Sending {1} docs took {2} seconds. Commit = {3}"
            log.debug(log_text.format(multiprocessing.current_process(), len(batch), time.time() - ts, commit))

    def process_batch(self, object_generator):
        batch = []
        more_objects = True
        processed_objects = 0
        while processed_objects < self.BATCH_SIZE:
            try:
                obj = next(object_generator)
                processed_objects = processed_objects + 1
                batch.append(ModelUpdate(obj, op=INDEX))
            except StopIteration:
                more_objects = False
                break        
        commit = not more_objects
        self._send_batch(batch, commit=commit)
        del batch
        return BatchResult(more_objects, processed_objects)


class ModelCatalogReindexer(object):

    def __init__(self, dmd):
        self.dmd = dmd
        self.indexer = zope.component.createObject('ModelIndex', get_solr_config())

    def _process_batch(self, object_generator, batch_size):
        batch_processor = BatchProcessor(self.indexer, batch_size)
        more_objects = batch_processor.process_batch(object_generator)
        del batch_processor
        return more_objects

    def reindex(self, root_path="", exclude_paths=None, batch_size=DEFAULT_BATCH_SIZE):
        if not root_path:
            root = self.dmd.getPhysicalRoot().zport
        else:
            root = self.dmd.unrestrictedTraverse(root_path)
        object_generator = CatalogableObjectsRetriever().get_catalogable_objects(root, exclude_paths)
        start = time.time()
        more_objects = True
        object_count = 0
        while more_objects:
            ts = time.time()
            batch_result = self._process_batch(object_generator, batch_size)
            more_objects = batch_result.more_objects
            object_count = object_count + batch_result.processed_objects
            log_text = "{0} - Processing batch of {1} docs took {2} seconds. Commit = {2}"
            log.debug(log_text.format(multiprocessing.current_process(), batch_size, time.time() - ts, not more_objects))
            transaction.abort()

        log.info("Reindexing {0} objects took {1} seconds.".format(object_count, time.time() - start))


def reindex_tree(root_path="", exclude_paths=None, batch_size=DEFAULT_BATCH_SIZE):
    log_text = "Starting thread {0} to reindex tree [{1}] excluding trees [{2}]"
    log.info(log_text.format(multiprocessing.current_process(), root_path, exclude_paths))
    dmd = ZenScriptBase(connect=True).dmd # get a connection to zodb
    start = time.time()
    ModelCatalogReindexer(dmd).reindex(root_path, exclude_paths, batch_size)
    log_text = "Thread {0} finished reindexing tree [{1}] in {2} seconds."
    log.info(log_text.format(multiprocessing.current_process(), root_path, time.time() - start))


def reindex(paths):
    # Uncomment this to run without workers
    #reindex_tree()
    #return
    workers = []
    if not isinstance(paths, set):
        paths = set(paths)
    # start the process that starts from the root
    main_tree = multiprocessing.Process(target=reindex_tree, args=("/zport", paths))
    workers.append(main_tree)

    for path in paths:
        exclude_paths = paths - set([path])
        worker = multiprocessing.Process(target=reindex_tree, args=(path, exclude_paths))
        workers.append(worker)

    for worker in workers:
        worker.start()
        time.sleep(2)

    while workers:
        workers = [ w for w in workers if w.is_alive() ]
        time.sleep(30)


def create_collection():
    solr_servers = get_solr_config()
    solr_client = SolrClient(solr_servers)

    if ZENOSS_MODEL_COLLECTION_NAME not in solr_client.get_collections():
        # @TODO we should read config values from file
        collection_config = {}
        collection_config["collection_name"] = ZENOSS_MODEL_COLLECTION_NAME
        collection_config["num_shards"] = 1
        solr_client.create_collection(collection_config)


def init():
    create_collection()
    # By default, we get separate threads to reindex Networks and Devices
    # @TODO spend some time thinking how to make reindexing as fast a possible
    #
    reindex( ("/zport/dmd/Networks", "/zport/dmd/Devices") )


if __name__ == "__main__":
    init()


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






