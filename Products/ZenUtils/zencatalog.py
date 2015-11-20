##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

import os
import sys
import logging
import time
import signal
import cPickle as pickle
from itertools import chain

from Globals import *

import transaction
from BTrees.OOBTree import OOSet
from Queue import Empty, Full
from multiprocessing import Process, Queue
from twisted.internet import defer, reactor, task
from OFS.ObjectManager import ObjectManager
from ZODB.POSException import ConflictError
from ZEO.Exceptions import ClientDisconnected
from ZEO.zrpc.error import DisconnectedError
from ZODB.transact import transact
from zope.component import getUtility
from Products.ManagableIndex.ManagableIndex import ManagableIndex
from Products.PluginIndexes.common import safe_callable
from Products.ZenRelations.ToManyContRelationship import ToManyContRelationship
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.ZenDaemon import ZenDaemon
from Products.ZenUtils.MultiPathIndex import MultiPathIndex
from Products.ZenUtils.MultiPathIndex import _isSequenceOfSequences
from Products.ZenUtils.MultiPathIndex import _recursivePathSplit
from Products.ZenUtils.Utils import zenPath
from Products.ZCatalog.Catalog import Catalog
from Products.Zuul.catalog.interfaces import IGlobalCatalogFactory
from Products.Zuul.catalog.global_catalog import GlobalCatalog
from Products.Zuul.catalog.global_catalog import catalog_caching
from Products.Zuul.catalog.global_catalog import initializeGlobalCatalog
from Products.Zuul.catalog.interfaces import IModelCatalog

log = logging.getLogger("zen.Catalog")

# Hide connection errors. We handle them all ourselves.
HIGHER_THAN_CRITICAL = 100
logging.getLogger('ZODB.Connection').setLevel(HIGHER_THAN_CRITICAL)
logging.getLogger('ZEO.zrpc').setLevel(HIGHER_THAN_CRITICAL)

PROGRESS_CHUNK_SIZE = 100
CALL_TREE_DUMP_FILE     = zenPath('var/zencatalog.call_tree.pickle')
PREVIOUS_UID_DUMP_FILE  = zenPath('var/zencatalog.previous_uid.pickle')
PRIMARY_PATHS_DUMP_FILE = zenPath('var/zencatalog.primary_paths.pickle')
BAD_PATHS_DUMP_FILE     = zenPath('var/zencatalog.bad_paths.pickle')
DOCUMENTS_DUMP_FILE     = zenPath('var/zencatalog.documents.pickle')

class CatalogReindexAborted(Exception): pass

def raiseKeyboardInterrupt(signum, frame):
    raise KeyboardInterrupt()

class ProgressCounter():
    def __init__(self, print_progress='.'):
        self.count = 0
        self.marker = print_progress
        self.print_progress = print_progress is not None

    def increment(self, delta=1):
      # optimized for understandability, rather than speed. :P
      for i in range(0,delta):
          self.count += 1
          if self.print_progress and (self.count % PROGRESS_CHUNK_SIZE) == 0:
              sys.stdout.write(self.marker)
              sys.stdout.flush()
      return self.count

def quietly_remove(filename):
    try:
        os.remove(filename)
    except OSError:
        pass

def ignore_interruptions():
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)

def drop_all_arguments():
    sys.argv[:] = sys.argv[:1]

def check_for_dead_parent():
    if (os.getppid() <= 1):
        log.warn("Detected death of parent process.")
        os._exit(1)

def put_or_die(queue, element):
    while True:
        try:
            queue.put_nowait(element)
        except Full:
            check_for_dead_parent()
            time.sleep(0.1)
            continue
        else:
            break

def check_for_interrupt(control):
    try:
        command = control.get_nowait()
        if command == 'stop':
            raise KeyboardInterrupt()
        else:
            log.warn("Ignoring unexpected command: %s" % command)
    except Empty:
        pass

def prime(q, filename):
    try:
        with open(filename, 'rb') as f:
            elements = pickle.load(f)
    except (pickle.PickleError, IOError):
        pass
    else:
        for e in elements:
            if e is not None:
                q.put(e)

def drain(q, filename=None):
    elements = []
    while True:
        try:
            e = q.get_nowait()
        except Empty:
            break
        except KeyboardInterrupt:
            pass
        if e is not None: elements.append(e)
    try:
        if filename:
            with open(filename, 'wb') as f:
                pickle.dump(elements, f)
    except (pickle.PickleError, IOError) as e:
        log.error("Error while draining queue to file: %s", filename)
        log.debug(elements)

def _reconnect(zc):
    if log.isEnabledFor(logging.DEBUG):
        log.debug("Lost DB connection. Attempting to reconnect.", exc_info=True)
    zc.syncdb()
    log.info("Reconnected")

def _get_global_catalog(zport):
    return getattr(zport, GlobalCatalog.id, None)

class RecursiveDefaultDict(dict):
    def __missing__(self, key):
        self[key] = RecursiveDefaultDict()
        return self[key]

# A sub-process
def source_from_zport(control, outbox, resume, print_progress=None):
    ignore_interruptions()
    drop_all_arguments()
    zc = ZenCatalog()
    zport = zc.dmd.getPhysicalRoot().zport
    counter = ProgressCounter(print_progress=print_progress)

    def find_kids(obj, call_tree):
        nones_counted = 0
        for kid in recurse(obj, call_tree):
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

    def recurse(obj, call_tree=None):
        if call_tree is None:
            call_tree = RecursiveDefaultDict()
        while True:
            check_for_dead_parent()
            check_for_interrupt(control)
            try:
                obj_id = obj.id
                tree = call_tree[obj_id]
                if tree is not False:
                    if not isinstance(obj, GlobalCatalog):
                        if isinstance(obj, ObjectManager):
                            for ob in obj.objectValues():
                                for kid in find_kids(ob, tree):
                                    yield kid
                            if isinstance(obj, ZenModelRM):
                                for rel in obj.getRelationships():
                                    if isinstance(rel, ToManyContRelationship):
                                        for kid in find_kids(rel, tree):
                                            yield kid
                                yield obj
                        elif isinstance(obj, ToManyContRelationship):
                            for ob in obj.objectValuesGen():
                                for kid in find_kids(ob, tree):
                                    yield kid
                    # invalidation allows object to be garbage collected
                    inv = getattr(obj, '_p_invalidate', None)
                    if inv is not None: inv()
                    call_tree[obj_id] = False
            except (ClientDisconnected, DisconnectedError):
                _reconnect(zc)
                continue
            except AttributeError:
                log.exception('Error in cataloging %s', obj.getPrimaryId())
            break
    try:
        if resume:
            with open(CALL_TREE_DUMP_FILE, 'rb') as f:
                call_tree = pickle.load(f)
        else:
            call_tree = RecursiveDefaultDict()
    except (pickle.PickleError, IOError):
        call_tree = RecursiveDefaultDict()
    try:
        with catalog_caching():
            tick = time.time()
            for obj in recurse(zport, call_tree):
                put_or_die(outbox, obj.getPrimaryPath())
                if (counter.increment() % 100 == 0) and (time.time() - tick) > 5.0:
                  transaction.abort() # allow garbage collection
                  tick = time.time()
    except KeyboardInterrupt:
        if call_tree:
            with open(CALL_TREE_DUMP_FILE, 'wb') as f:
                pickle.dump(call_tree, f)
    else:
        quietly_remove(CALL_TREE_DUMP_FILE)
    finally:
        transaction.abort()

# A sub-process
def source_from_catalog(control, outbox, resume, print_progress=None):
    ignore_interruptions()
    drop_all_arguments()
    zc = ZenCatalog()
    dmd = zc.dmd
    zport = dmd.getPhysicalRoot().zport
    catalog = dmd.global_catalog
    counter = ProgressCounter(print_progress=print_progress)

    try:
        if resume:
            with open(PREVIOUS_UID_DUMP_FILE, 'rb') as f:
                previous_uid = pickle.load(f)
        else:
            previous_uid = None
    except (pickle.PickleError, IOError):
        previous_uid = None
    try:
        while True:
            try:
                if previous_uid is None:
                    uids = catalog._catalog.uids.iterkeys()
                else:
                    uids = catalog._catalog.uids.iterkeys(min=previous_uid,
                                                          excludemin=True)
                for uid in uids:
                    check_for_dead_parent()
                    check_for_interrupt(control)
                    put_or_die(outbox, uid)
                    previous_uid = uid
                    counter.increment()
            except (AttributeError, ClientDisconnected, DisconnectedError):
                _reconnect(zc)
                continue
            break
    except KeyboardInterrupt:
        if previous_uid is not None:
            with open(PREVIOUS_UID_DUMP_FILE, 'wb') as f:
                pickle.dump(previous_uid, f)
    else:
        quietly_remove(PREVIOUS_UID_DUMP_FILE)

# Used by catalog_the_things, commit_to_catalog, and remove_from_catalog.
def commit_in_batches(zc, buffer_consumer, inbox, buffer_size, counter=None):
    _commit_buffer = transact(buffer_consumer)

    def commit_buffer(buf):
        while True:
            try:
                return _commit_buffer(buf)
            except (AttributeError, ClientDisconnected, DisconnectedError):
                _reconnect(zc)
                continue

    buffer = []
    try:
        while True:
            try:
                element = inbox.get_nowait()
            except Empty:
                check_for_dead_parent()
                time.sleep(0.1)
                continue
            if element is None:
                # End of inbox. We're done here.
                break
            buffer.append(element)
            if len(buffer) >= buffer_size:
                delta = commit_buffer(buffer)
                if counter:
                    if delta is None:
                        delta = len(buffer)
                    counter.increment(delta)
                buffer = []
    finally:
        try:
            delta = commit_buffer(buffer)
        except BaseException:
            log.warn("Failed to commit some changes.", exc_info=True)
            for element in buffer:
                put_or_die(inbox, element)
        else:
            if counter:
                if delta is None:
                    delta = len(buffer)
                counter.increment(delta)

# A sub-process
def catalog_the_things(worker_id, inbox, trash, buffer_size, permissions_only, print_progress=None):
    # We don't import this above, because it didn't exist prior to 4.2.
    # It's safe to import here, because we only get here if the CatalogService
    # is installed, which didn't exist until 4.2.
    from Products.Zuul.catalog.global_catalog import initializeGlobalCatalog

    ignore_interruptions()
    drop_all_arguments()
    zc             = ZenCatalog()
    dmd            = zc.dmd
    zport          = dmd.getPhysicalRoot().zport
    global_catalog = _get_global_catalog(zport)
    catalog_id     = local_catalog_id(worker_id)

    def _create_local_catalog():
        local_catalog  = global_catalog.__class__()
        initializeGlobalCatalog(local_catalog)
        try:
           zport._delObject(catalog_id)
        except:
           pass
        zport._setObject(catalog_id, local_catalog)

    create_local_catalog = transact(_create_local_catalog, retries=100)
    create_local_catalog()
    local_catalog  = getattr(zport, catalog_id, None)
    catalog        = local_catalog._catalog
    counter        = ProgressCounter(print_progress=print_progress)

    def _catalog_one(primary_path):
        try:
            obj = dmd.unrestrictedTraverse(primary_path)
        except (AttributeError, ClientDisconnected, DisconnectedError):
            raise
        except Exception:
            log.debug("Could not load object: %s", primary_path)
            put_or_die(trash, primary_path)
            return False
        if obj is None:
            log.debug("%s does not exist", primary_path)
            put_or_die(trash, primary_path)
            return False
        try:
            uid = global_catalog._catalog.uids.get(primary_path, None)
            if uid is not None:
                catalog.uids[primary_path] = uid
                catalog.paths[uid] = global_catalog._catalog.paths.get(uid, None)
                catalog.data[uid] = global_catalog._catalog.data.get(uid, None)
            if permissions_only:
                catalog.catalog_object(obj, update_metadata=False,
                                            idxs=("allowedRolesAndUsers",))
            else:
                # We intentionally don't do legacy indexing:
                # if hasattr(obj, 'index_object'): obj.index_object()
                catalog.catalog_object(obj)
                getUtility(IModelCatalog).catalog_object(obj)  # TEMP to be able to index model catalog
        except (AttributeError, ClientDisconnected, DisconnectedError):
            raise
        except Exception:
            log.info("Error cataloging object %s. Skipping", primary_path,
                     exc_info=(log.isEnabledFor(logging.DEBUG)))
            return False
        return True

    def _catalog_several(primary_paths):
        dmd._p_jar.sync()
        count = 0
        for primary_path in primary_paths:
            if _catalog_one(primary_path):
                count += 1
        return count

    commit_in_batches(zc, _catalog_several, inbox, buffer_size, counter)

# A sub-process
def convert_into_document(worker_id, inbox, outbox, buffer_size, permissions_only, print_progress=None):
    ignore_interruptions()
    drop_all_arguments()
    zc          = ZenCatalog()
    dmd         = zc.dmd
    zport       = dmd.getPhysicalRoot().zport
    catalog     = dmd.global_catalog
    vals        = []
    documentIds = []
    uids        = []
    counter     = ProgressCounter(print_progress=print_progress)

    # Apply monkey patches ...
    def index_object(self, documentId, obj, threshold=None):
        val= self._evaluate(obj)
      
        cuv = self._val2UnindexVal
        if val is not None and cuv is not None: unindexVal = cuv(val)
        else: unindexVal = val

        documentIds.append(documentId)

        if val is not None:
            vals.append((self.id, val, unindexVal))
            return 1
        return 0
    ManagableIndex.index_object = index_object

    def mpi_index_object(self, docId, obj, threshold=None):
        f = getattr(obj, self.id, None)
        if f is not None:
            if safe_callable(f):
                try:
                    paths = f()
                except AttributeError:
                    return 0
            else:
                paths = f
        else:
            try:
                paths = obj.getPhysicalPath()
            except AttributeError:
                return 0
        if paths:
            paths = _recursivePathSplit(paths)
            if not _isSequenceOfSequences(paths):
                paths = [paths]
            vals.append((self.id, paths, None))
            return 1
        return 0
    MultiPathIndex.index_object = mpi_index_object


    orig_catalogObject = Catalog.catalogObject
    def catalogObject(self, object, uid, threshold=None, 
                      idxs=None, update_metadata=1):
        uids.append(uid)
        return orig_catalogObject(self, object, uid, threshold, 
                                  idxs, update_metadata)
    Catalog.catalogObject = catalogObject

    def convertToDocument(primary_path):
        while True:
            try:
                try:
                    obj = dmd.unrestrictedTraverse(primary_path)
                except (AttributeError, ClientDisconnected, DisconnectedError):
                    raise
                except Exception:
                    log.debug("Could not load object: %s", primary_path)
                    put_or_die(outbox, (None, primary_path, None, None)) # uncatalog
                    counter.increment()
                    continue
                if obj is None:
                    log.debug("%s does not exist", primary_path)
                    put_or_die(outbox, (None, primary_path, None, None)) # uncatalog
                    counter.increment()
                    continue
                if permissions_only:
                    catalog.catalog_object(obj, update_metadata=False,
                                                idxs=("allowedRolesAndUsers",))
                else:
                    # We intentionally don't do legacy indexing:
                    # if hasattr(obj, 'index_object'): obj.index_object()
                    catalog.catalog_object(obj)
                    getUtility(IModelCatalog).catalog_object(obj)  # TEMP to be able to index model catalog
                if documentIds:
                    uid = uids.pop()
                    documentId = documentIds[0]
                    metadata = catalog._catalog.data.get(documentId, {})
                    put_or_die(outbox, (documentId, uid[:], vals[:], metadata))
                    counter.increment()
            except (AttributeError, ClientDisconnected, DisconnectedError):
                reconnect(zc)
                continue
            finally:
                # clear lists
                vals[:] = []
                uids[:] = []
                documentIds[:] = []
                # Invalidation allows object to be garbage collected
                inv = getattr(obj, '_p_invalidate', None)
                if inv is not None: inv()
            break

    # Process my inbox ...
    with catalog_caching():
        tick = time.time()
        while True:
            try:
                if (counter.count % 100 == 0) and (time.time() - tick > 5.0):
                  transaction.abort() # Allow garbage collection
                  tick = time.time()
                primary_path = inbox.get_nowait()
            except Empty:
                check_for_dead_parent()
                time.sleep(0.1)
                continue
            if primary_path is None:
                break # End of inbox. We're done here.
            try:
                convertToDocument(primary_path)
            except Exception:
                log.info("Error indexing object %s. Skipping.", primary_path,
                         exc_info = log.isEnabledFor(logging.DEBUG))

# A sub-process
def remove_from_catalog(inbox, counts, buffer_size, print_progress=None):
    ignore_interruptions()
    drop_all_arguments()
    zc             = ZenCatalog()
    dmd            = zc.dmd
    global_catalog = dmd.global_catalog
    counter        = ProgressCounter(print_progress=print_progress)

    def consume(buf):
        dmd._p_jar.sync()
        for bad_path in buf:
            global_catalog.uncatalog_object(bad_path)

    commit_in_batches(zc, consume, inbox, buffer_size, counter)
    put_or_die(counts, counter.count)

# A sub-process
def commit_to_catalog(inbox, counts, buffer_size, print_progress=None):
    ignore_interruptions()
    drop_all_arguments()
    zc             = ZenCatalog()
    dmd            = zc.dmd
    global_catalog = dmd.global_catalog
    catalog        = global_catalog._catalog
    counter        = ProgressCounter(print_progress=print_progress)

    def consume(buf):
        dmd._p_jar.sync()
        for docId, uid, ob, metadata in buf:
            if uid is not None and docId is None:
                global_catalog.uncatalog_object(uid)
                continue
            if uid not in catalog.uids:
                catalog._length.change(1)
            catalog.uids[uid] = docId
            catalog.paths[docId] = uid
            if metadata:
                catalog.data[docId] = metadata
            for idx, val, uval in ob:
                if val is not None:
                    idx = catalog.indexes[idx]
                    if isinstance(idx, MultiPathIndex):
                        if docId in idx._unindex:
                            unin = idx._unindex[docId]
                            if isinstance(unin, set):
                                unin = self._unindex[docId] = OOSet(unin)
                            for oldpath in list(unin):
                                if list(oldpath.split('/')) not in val:
                                    idx.unindex_paths(docId, (oldpath,))
                        else:
                            idx._unindex[docId] = OOSet()
                            idx._length.change(1)
                        idx.index_paths(docId, val)
                    else:
                        oldval = idx._unindex.get(docId)
                        if uval == oldval: continue
                        customEq = idx._equalValues
                        if customEq is not None:
                            if customEq(val,oldval): continue
                        update = idx._update
                        if update is None or oldval is None or val is None:
                            if oldval is not None:
                                idx._unindex_object(docId,oldval,val is None)
                            if val is None: continue
                            idx._indexValue(docId, val, None)
                            if oldval is None: idx.numObjects.change(1)
                        else:
                            rv = update(docId, val, oldval, None)
                            if isinstance(rv, tuple): continue
                        idx._unindex[docId] = uval

    commit_in_batches(zc, consume, inbox, buffer_size, counter)
    put_or_die(counts, counter.count)

# A sub-process, exit code is zero if and only if the catalog service is installed.
def check_for_catalog_service():
    ignore_interruptions()
    drop_all_arguments()
    zc = ZenCatalog()
    klass = zc.dmd.global_catalog.__class__
    try:
        from ZenPacks.zenoss.CatalogService.GlobalCatalog \
            import GlobalCatalog as CatalogServiceGlobalCatalog
        if klass == CatalogServiceGlobalCatalog:
            sys.exit(0)
    except Exception:
        pass
    sys.exit(1)

# A sub-process, exit code is zero if and only if the global catalog exists.
def check_for_global_catalog():
    ignore_interruptions()
    drop_all_arguments()
    zc = ZenCatalog()
    zport = zc.dmd.getPhysicalRoot().zport
    if (_get_global_catalog(zport) is None):
        sys.exit(1)
    else:
        sys.exit(0)

# A sub-process, exit code is zero if and only if we actually create
# (or replace) the global catalog.
def create_new_global_catalog(force):
    ignore_interruptions()
    drop_all_arguments()
    zc = ZenCatalog()

    @transact
    def do_it():
        zport = zc.dmd.getPhysicalRoot().zport
        catalog = _get_global_catalog(zport)
        factory = getUtility(IGlobalCatalogFactory)
        if force and catalog:
            factory.remove(zport)
            catalog = _get_global_catalog(zport)
        if catalog is None:
            log.debug("Creating global catalog")
            zport = zc.dmd.getPhysicalRoot().zport
            factory.create(zport)
            return True
        else:
            return False
    if do_it():
        sys.exit(0)
    else:
        sys.exit(1)

def local_catalog_id(worker_id):
    return GlobalCatalog.id + ('_for_zencatalog_worker_%d' % worker_id)

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
            help="Only works with --reindex, only update "\
                 " the permissions catalog")
        self.parser.add_option("--resume",
            action="store_true",
            default=False,
            help="continue indexing after an interruption")
        self.parser.add_option("--clearmemcached",
            action="store_true",
            default=False,
            help="clears memcached after processing")
        self.parser.add_option("--workers",
            type="int",
            default=4,
            help="Number of processes working simultaneously")
        self.parser.add_option("--buffersize",
            type="int",
            default=200,
            help="Number of indexed documents to batch up in one commit")
        self.parser.add_option("--inputqueuesize",
            type="int",
            default=300,
            help="Maximum number of objects to have backlogged to process")
        self.parser.add_option("--processedqueuesize",
            type="int",
            default=300,
            help="Maximum number of objects to have backlogged to commit")

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

    def _setup_queues(self, input_queue_size, processed_queue_size, resume):
        self.command_q      = Queue()
        self.primary_path_q = Queue(input_queue_size)
        self.bad_path_q     = Queue(processed_queue_size)
        self.document_q     = Queue(processed_queue_size)
        self.count_q        = Queue()

        if resume:
            prime(self.primary_path_q, PRIMARY_PATHS_DUMP_FILE)
            prime(self.bad_path_q, BAD_PATHS_DUMP_FILE)
            prime(self.document_q, DOCUMENTS_DUMP_FILE)

    def _drain_queues(self):
        drain(self.primary_path_q, PRIMARY_PATHS_DUMP_FILE)
        drain(self.bad_path_q, BAD_PATHS_DUMP_FILE)
        drain(self.document_q, DOCUMENTS_DUMP_FILE)

    def _cleanup_dump_files(self):
        quietly_remove(BAD_PATHS_DUMP_FILE)
        quietly_remove(DOCUMENTS_DUMP_FILE)
        quietly_remove(PRIMARY_PATHS_DUMP_FILE)
        quietly_remove(PREVIOUS_UID_DUMP_FILE)
        quietly_remove(CALL_TREE_DUMP_FILE)

    def _setup_source(self, source_target, resume, print_progress=None):
        self.source = Process(
            target=source_target,
            args=(self.command_q, self.primary_path_q, resume)
        )
        self.source.daemon = True

    def _setup_workers(self, worker_target, worker_count, input_q, output_q, buffer_size, permissions_only, print_progress=None):
        self.workers = []
        for worker_id in range(worker_count):
            p = Process(
                    target=worker_target,
                    args=(worker_id, input_q, output_q, buffer_size, permissions_only, print_progress and '.')
                )
            p.daemon = True
            self.workers.append(p)

    def _setup_finisher(self, finisher_target, input_q, buffer_size, print_progress=None):
        self.finisher = Process(
            target=finisher_target,
            args=(input_q, self.count_q, buffer_size)
        )
        self.finisher.daemon = True

    def _start_children(self):
        self.finisher.start()
        for worker in self.workers:
            worker.start()
        self.source.start()
        self.aborted = False
        self.count_committed = 0

    def _put_sentinal_value(self, q, sentinal=None):
        try:
            q.put_nowait(sentinal)
            return True
        except Full:
            return False

    def _wait_for_children(self, print_progress):
        count = None
        while True:
            try:
                if self.source.is_alive(): self.source.join()
                while self.workers:
                    self.workers[:] = [w for w in self.workers if w.is_alive()]
                    for worker in self.workers:
                        self._put_sentinal_value(self.primary_path_q)
                    time.sleep(0.1)
                while self.finisher.is_alive():
                    self._put_sentinal_value(self.bad_path_q)
                    self._put_sentinal_value(self.document_q)
                    time.sleep(0.1)
                self._drain_queues()
                while True:
                    try:
                        if count is None:
                            count = self.count_q.get_nowait()
                        if count is not None:
                            # tiny race condition here if we get a KeyboardInterrupt
                            self.count_committed += count
                            count = None
                    except Empty:
                        break
                if print_progress:
                    sys.stdout.write('\n')
            except KeyboardInterrupt:
                if self.source.is_alive():
                    if self._put_sentinal_value(self.command_q, 'stop'):
                        self.aborted = True
                continue
            break

    def _after_processing(self, zc):
        log.info("Committed %d (Total: %d)" % (self.count_committed, len(zc.dmd.global_catalog)))
        if self.aborted:
            raise CatalogReindexAborted()
        else:
            self._cleanup_dump_files()
            log.debug("Marking the indexing as completed in the database")
            zc.syncdb()
            zc.dmd.getPhysicalRoot().zport._zencatalog_completed = True
            transaction.commit()

    def _process_catalog_service(self, source_target, worker_count, buffer_size, input_queue_size, processed_queue_size, resume, permissions_only, print_progress):
        self._setup_queues(input_queue_size, processed_queue_size, resume)
        self._setup_source(source_target, resume, print_progress)
        self._setup_workers(catalog_the_things, worker_count, self.primary_path_q, self.bad_path_q, buffer_size, permissions_only, print_progress)
        self._setup_finisher(remove_from_catalog, self.bad_path_q, buffer_size, print_progress)
        self._start_children()
        self._wait_for_children(print_progress)

        log.info("Merging catalog updates from worker processes into global catalog")
        drop_all_arguments()        
        zc = ZenCatalog()
        dmd = zc.dmd
        zport = dmd.zport
        global_catalog = dmd.global_catalog
        for i in range(worker_count):
            catalog_id = local_catalog_id(i)
            worker_catalog = getattr(zport, catalog_id, None)
            if worker_catalog:
                self.count_committed += len(worker_catalog._catalog.paths)
                global_catalog._catalog.uids.update(worker_catalog._catalog.uids)
                global_catalog._catalog.paths.update(worker_catalog._catalog.paths)
                global_catalog._catalog.data.update(worker_catalog._catalog.data)
                zport._delObject(catalog_id)
            if print_progress:
                sys.stdout.write('.')
                sys.stdout.flush()
        if print_progress:
            sys.stdout.write('\n')
        new_length = len(global_catalog._catalog.paths)
        global_catalog._catalog._length.set(new_length)
        transaction.commit()

        self._after_processing(zc)

    def _process_zcatalog(self, source_target, worker_count, buffer_size, input_queue_size, processed_queue_size, resume, permissions_only, print_progress):
        if buffer_size > processed_queue_size: buffer_size = processed_queue_size
        self._setup_queues(input_queue_size, processed_queue_size, resume)
        self._setup_source(source_target, resume, print_progress)
        self._setup_workers(convert_into_document, worker_count, self.primary_path_q, self.document_q, buffer_size, permissions_only, print_progress)
        self._setup_finisher(commit_to_catalog, self.document_q, buffer_size, print_progress)
        self._start_children()
        self._wait_for_children(print_progress)

        drop_all_arguments()
        zc = ZenCatalog()
        self._after_processing(zc)

    def _process(self, source_target, worker_count, buffer_size, input_queue_size, processed_queue_size, resume, permissions_only, print_progress):
        if self._check_for_catalog_service():
            processor = self._process_catalog_service
        else:
            processor = self._process_zcatalog
        processor(source_target, worker_count, buffer_size, input_queue_size, processed_queue_size, resume, permissions_only, print_progress)

    def _create_catalog(self, worker_count, buffer_size, input_queue_size, processed_queue_size, force=False, clearmemcached=False, resume=True, print_progress=True):
        if force:
            if resume:
                log.info("--forceindex is incompatible with --resume, "\
                         "Pick --forceindex to start over completely, or "\
                         "--resume to continue indexing from interruption.")
                return False
            self._cleanup_dump_files()
        if self._create_new_global_catalog(force):
            pass
        elif os.path.isfile(CALL_TREE_DUMP_FILE):
            if resume:
                pass
            else:
                log.info("Global catalog already exists. "\
                         "Run with --forceindex to drop and recreate catalog, "\
                         "or --resume to continue indexing from interruption.")
                return False
        else:
            log.info("Global catalog already exists. "\
                     "Run with --forceindex to drop and recreate catalog.")
            return False

        log.info("Recataloging your system. This may take some time.")
        start_time = time.time()
        try:
            self._process(source_target=source_from_zport,
                          worker_count=worker_count,
                          buffer_size=buffer_size,
                          input_queue_size=input_queue_size,
                          processed_queue_size=processed_queue_size,
                          resume=resume,
                          permissions_only=False,
                          print_progress=print_progress)
        except CatalogReindexAborted:
            total_time = time.time() - start_time
            log.info("Aborted! (%1.1f seconds) Try running with --resume.", total_time)
            return False
        else:
            total_time = time.time() - start_time
            log.info("Cataloging completed in %1.1f seconds.", total_time)
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
        start_time = time.time()
        try:
            self._process(source_target=source_from_catalog,
                          worker_count=worker_count,
                          buffer_size=buffer_size,
                          input_queue_size=input_queue_size,
                          processed_queue_size=processed_queue_size,
                          resume=resume,
                          permissions_only=permissions_only,
                          print_progress=print_progress)
        except CatalogReindexAborted:
            total_time = time.time() - start_time
            log.info("Aborted! (%1.1f seconds) Try running with --resume.", total_time)
            return False
        else:
            total_time = time.time() - start_time
            log.info("Reindexing completed in %1.1f seconds.", total_time)
            return True
 
    def _create_new_global_catalog(self, force=False):
        p = Process(target=create_new_global_catalog, args=(force,))
        p.daemon = True
        p.start()
        p.join()
        if p.exitcode < 0:
            raise CatalogReindexAborted()
        else:
            return p.exitcode == 0

    def _check_for_global_catalog(self):
        p = Process(target=check_for_global_catalog)
        p.daemon = True
        p.start()
        p.join()
        if p.exitcode < 0:
            raise CatalogReindexAborted()
        else:
            return p.exitcode == 0

    def _check_for_catalog_service(self):
        p = Process(target=check_for_catalog_service)
        p.daemon = True
        p.start()
        p.join()
        if p.exitcode < 0:
            raise CatalogReindexAborted()
        else:
            return p.exitcode == 0

class ZenCatalog(ZCmdBase): pass

def reindex_catalog(zport, permissionsOnly=False, printProgress=True, commit=True):
    globalCat = zport.global_catalog
    with catalog_caching():
        msg = 'objects'
        if permissionsOnly:
            msg = 'permissions'
        log.info('reindexing %s in catalog' % msg)
        i = 0
        catObj = globalCat.catalog_object
        for brain in globalCat():
            log.debug('indexing %s' % brain.getPath())
            try:
                obj = brain.getObject()
            except Exception:
                log.debug("Could not load object: %s" % brain.getPath())
                globalCat.uncatalog_object(brain.getPath())
                continue
            if obj is not None:
                #None defaults to all inedexs
                kwargs = {}
                if permissionsOnly:
                    kwargs = {'update_metadata': False,
                              'idxs': ("allowedRolesAndUsers",)}
                elif hasattr(obj, 'index_object'):
                    obj.index_object()

                catObj(obj, **kwargs)
                log.debug('Catalogued object %s' % obj.absolute_url_path())
            else:
                log.debug('%s does not exists' % brain.getPath())
                globalCat.uncatalog_object(brain.getPath())
            i += 1
            if not i % PROGRESS_CHUNK_SIZE:
                if printProgress:
                    sys.stdout.write(".")
                    sys.stdout.flush()
                else:
                    log.info('Catalogued %s objects' % i)
                if commit:
                    transaction.commit()
        if printProgress:
            sys.stdout.write('\n')
            sys.stdout.flush()
        if commit:
            transaction.commit()

if __name__ == "__main__":
    zc = ZenCatalogBase()
    try:
        signal.signal(signal.SIGTERM, raiseKeyboardInterrupt)
        zc.run()
    except Exception:
        log.exception("Failed!")
