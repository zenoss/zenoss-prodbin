
import logging
import transaction
import zope.component

from Acquisition import aq_parent, Implicit
from interfaces import IModelCatalog
from collections import defaultdict
from Products.AdvancedQuery import And, Or, Eq
from Products.ZCatalog.interfaces import ICatalogBrain
from Products.ZenModel.Software import Software
from Products.ZenModel.OperatingSystem import OperatingSystem
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.Zuul.catalog.interfaces import IIndexableWrapper
from transaction.interfaces import IDataManager
from zenoss.modelindex import indexed, index
from zenoss.modelindex.field_types import StringFieldType, \
     ListOfStringsFieldType, IntFieldType, DictAsStringsFieldType, LongFieldType
from zenoss.modelindex.constants import INDEX_UNIQUE_FIELD as UID
from zenoss.modelindex.exceptions import IndexException, SearchException
from zenoss.modelindex.model_index import ModelUpdate, INDEX, UNINDEX, SearchParams

from zope.component import getGlobalSiteManager, getUtility
from zope.interface import implements

import traceback

log = logging.getLogger("model_catalog")

#logging.getLogger("requests").setLevel(logging.ERROR) # requests can be pretty chatty 


class ModelCatalogError(Exception):
    def __init__(self, message=""):
        if not message:
            message = "Model Catalog internal error"
        super(ModelCatalogError, self).__init__(message)


class ModelCatalogUnavailableError(ModelCatalogError):
    def __init__(self, message = ""):
        if not message:
            message = "Model Catalog not available"
        super(ModelCatalogUnavailableError, self).__init__(message)


class SearchResults(object):

    def __init__(self, results, total, hash_, areBrains=True):
        self.results = results
        self.total = total
        self.hash_ = hash_
        self.areBrains = areBrains

    def __hash__(self):
        return self.hash_

    def __iter__(self):
        return self.results


class ModelCatalogBrain(Implicit):
    implements(ICatalogBrain)

    def __init__(self, result):
        """
        Modelindex result wrapper
        @param result: modelindex.zenoss.modelindex.search.SearchResult
        """
        self._result = result
        for idx in result.idxs:
            setattr(self, idx, getattr(result, idx, None))

    def has_key(self, key):
        return self.__contains__(key)

    def __contains__(self, name):
        return hasattr(self._result, name)

    def getPath(self):
        """ Get the physical path for this record """
        uid = str(self._result.uid)
        if not uid.startswith('/zport/dmd'):
            uid = '/zport/dmd/' + uid
        return uid

    def _unrestrictedGetObject(self):
        """ """
        return self.getObject()

    def getObject(self):
        """Return the object for this record

        Will return None if the object cannot be found via its cataloged path
        (i.e., it was deleted or moved without recataloging), or if the user is
        not authorized to access the object.
        """
        parent = aq_parent(self)
        obj = None
        try:
            obj = parent.unrestrictedTraverse(self.getPath())
        except:
            log.error("Unable to get object from brain. Path: {0}. Catalog may be out of sync.".format(self._result.uid))
        return obj

    def getRID(self):
        """Return the record ID for this object."""
        return self._result.uuid


class ModelCatalogClient(object):

    def __init__(self, solr_url):
        self._data_manager = ModelCatalogDataManager(solr_url)

    def _get_forbidden_classes(self):
        return (Software, OperatingSystem)

    def get_indexes(self):
        return self._data_manager.get_indexes()

    def search(self, search_params, context):
        return self._data_manager.search(search_params, context)

    def catalog_object(self, obj, idxs=None):
        if not isinstance(obj, self._get_forbidden_classes()):
            try:
                self._data_manager.add_model_update(ModelUpdate(obj, op=INDEX, idxs=idxs))
            except IndexException as e:
                log.error("EXCEPTION {0} {1}".format(e, e.message))
                self._data_manager.raise_model_catalog_error()

    def uncatalog_object(self, obj):
        if not isinstance(obj, self._get_forbidden_classes()):
            try:
                self._data_manager.add_model_update(ModelUpdate(obj, op=UNINDEX))
            except IndexException as e:
                log.error("EXCEPTION {0} {1}".format(e, e.message))
                self._data_manager.raise_model_catalog_error()


class NoRollbackSavepoint(object):
    def __init__(self, datamanager):
        self.datamanager = datamanager

    def rollback(self):
        pass


TX_SEPARATOR = "@=@"


class ModelCatalogTransactionState(object):
    """ This class stores all the infromation about objects updated during a transaction """

    def __init__(self, tid):
        """ """
        self.tid = tid
        # @TODO For the time being we only have two index operations INDEX and UNINDEX
        # Once we are able to index only certain indexes and use solr
        # atomic updates this will become more complex in order to send as few requests to solr
        # as possible
        #
        # model_update may become a list of updates when we support more
        # operations other than INDEX, UNINDEX
        #
        self.pending_updates = {}  # { object_uid :  model_update }
        self.indexed_updates = {}  # { object_uid :  model_update }
        # ^^
        # In indexed_updates we store updates that we indexed mid transaction
        # because a search came in. Only this transaction should see such changes
        self.temp_indexed_uids = set() # uids (uid@=@tid) of temporary indexed documents
        self.commits_metric = []

    def add_model_update(self, update):
        # When we support atomic updates the logic to combine multiple
        # atomic updates for an object will be here. For now as we only can
        # index/unindex the last update overwrites any previous one
        #
        self.pending_updates[update.uid]=update

    def get_pending_updates(self):
        """ return updates that have not been sent to the index """
        return self.pending_updates.values()

    def get_indexed_updates(self):
        return self.indexed_updates.values()

    def get_updates_to_finish_transaction(self):
        #
        self.commits_metric.append(len(self.pending_updates))
        # Get all updates
        final_updates = {}
        for uid, update in self.indexed_updates.iteritems():
            # update the uid and tx_state
            if update.op == INDEX:
                update.spec.set_field_value("uid", uid)
                update.spec.set_field_value("tx_state", 0)
            final_updates[uid] = update
        # now update overwriting in case we had a new update for any
        # of the already indexed objects
        final_updates.update(self.pending_updates)
        return final_updates.values()

    def are_there_pending_updates(self):
        return len(self.pending_updates) > 0

    def are_there_indexed_updates(self):
        return len(self.indexed_updates) > 0

    def mark_pending_updates_as_indexed(self, indexed_uids):
        """
        @param indexed_uids: temporary uids we indexed the docs with
        """
        self.commits_metric.append(len(self.pending_updates))
        self.temp_indexed_uids = self.temp_indexed_uids | indexed_uids
        self.indexed_updates.update(self.pending_updates)
        self.pending_updates = {} # clear pending updates
        log.warn("SEARCH TRIGGERED TEMP INDEXING. {0}".format(traceback.format_stack()))   # @TODO TEMP LOGGING


class ModelCatalogDataManager(object):
    """ Class that interfaces with the modelindex package to interact with solr """

    implements(IDataManager)

    def __init__(self, solr_servers):
        self.model_index = zope.component.createObject('ModelIndex', solr_servers)
        self._current_transactions = {} # { transaction_id : ModelCatalogTransactionState }
        # @TODO ^^ Make that an OOBTREE to avoid concurrency issues? I dont think we need it since we have one per thread

    def _get_tid(self, tx=None):
        if tx is None:
            tx = transaction.get()
        return id(tx)

    def _get_tx_state(self, tx=None):
        tid = self._get_tid(tx)
        return self._current_transactions.get(tid)

    def ping_index(self):
        return self.model_index.ping()

    def get_indexes(self):
        return self.model_index.get_indexes()

    def _process_pending_updates(self, tx_state):
        updates = tx_state.get_pending_updates()
        # we are going to index all pending updates adding
        # the tid to the uid field and setting tx_state field
        # to the tid
        tweaked_updates = []
        indexed_uids = set()
        for update in updates:
            tid = tx_state.tid
            temp_uid = "{0}{1}{2}".format(update.uid, TX_SEPARATOR, tid)

            # We only unindex docs that have been already modified
            # unmodified docs marked for removal are not a problem since
            # we blacklist them from searchs
            if update.op == UNINDEX:
                if temp_uid not in tx_state.temp_indexed_uids:
                    continue
                else:
                    update.uid = temp_uid
            else:
                # Index the object with a special uid
                update.spec.set_field_value("uid", temp_uid)
                update.spec.set_field_value("tx_state", tid)
                indexed_uids.add(temp_uid)
            tweaked_updates.append(update)

        # send and commit indexed docs to solr
        self.model_index.process_model_updates(tweaked_updates)
        # marked docs as indexed
        tx_state.mark_pending_updates_as_indexed(indexed_uids)

    def _add_tx_state_query(self, search_params, tx_state):
        """
        only interested in docs indexed by committed transactions or
        in docs temporary committed by the current transaction
        """
        values = [ 0 ]  # default tx_state for committed transactions
        if tx_state:
            values.append(tx_state.tid)
        if isinstance(search_params.query, dict):
            search_params.query["tx_state"] = values
        else: # We assume it is an AdvancedQuery
            or_query = [ Eq("tx_state", value) for value in values]
            search_params.query = And( search_params.query, Or(*or_query) )
        return search_params

    def raise_model_catalog_error(self, message=""):
        if not self.ping_index():
            raise ModelCatalogUnavailableError(message)
        else:
            raise ModelCatalogError(message)

    def _parse_catalog_results(self, catalog_results, context):
        """
        build brains from model catalog results. It also
        tweaks the results filtering outdated objects
        """
        tx_state = self._get_tx_state()
        tweak_results = (tx_state and tx_state.are_there_indexed_updates())
        dirty_uids = temp_indexed_uids = set()
        if tweak_results:
            dirty_uids = set(tx_state.indexed_updates.keys())
            temp_indexed_uids = tx_state.temp_indexed_uids
        brains = []
        count = 0
        for result in catalog_results.results:
            if tweak_results:
                if result.uid in dirty_uids:
                    continue  # outdated result
                elif result.uid in temp_indexed_uids:
                    result.uid = result.uid.split(TX_SEPARATOR)[0]
            brain = ModelCatalogBrain(result)
            brain = brain.__of__(context.dmd)
            brains.append(brain)
            count = count + 1
        return SearchResults(iter(brains), total=count, hash_=str(count))

    def _do_search(self, search_params, context):
        """
        @param  context object to hook brains up to acquisition
        """
        try:
            catalog_results = self.model_index.search(search_params)
        except SearchException as e:
            log.error("EXCEPTION: {0}".format(e.message))
            self.raise_model_catalog_error()
        return self._parse_catalog_results(catalog_results, context)

    def search(self, search_params, context):
        """
        When we do a search mid-transaction and there are objects that have already been modified and not
        indexed, we need to index and commit them before performing the search.
        Mid-transaction changes can only be visible by the current transaction until the tx is committed.
        Hopefully most transactions won't do searches after updating objects so we can minimize the number 
        of commits to solr
        """
        search_results = None
        tx_state = self._get_tx_state()
        # Lets add tx_state filters
        search_params = self._add_tx_state_query(search_params, tx_state)
        if tx_state and tx_state.are_there_pending_updates():
            # Temporary index updated objects so the search
            # is accurate
            self._process_pending_updates(tx_state)

        return self._do_search(search_params, context)

    # ----- Index related methods  ------

    def reset_tx_state(self, tx):
        tid = self._get_tid(tx)
        if tid in self._current_transactions:
            del self._current_transactions[tid]

    def add_model_update(self, update):
        tx = transaction.get()
        tid = self._get_tid(tx)
        if tid not in self._current_transactions:
            tx.join(self)
            self._current_transactions[tid] = ModelCatalogTransactionState(tid)
        tx_state = self._current_transactions[tid]
        tx_state.add_model_update(update)

    def _delete_temporary_tx_documents(self):
        tx_state = self._get_tx_state()
        if tx_state and tx_state.are_there_indexed_updates():
            try:
                query = {"tx_state":tx_state.tid}
                self.model_index.unindex_search(SearchParams(query))
            except Exception as e:
                log.fatal("Exception trying to abort current transaction. {0} / {1}".format(e, e.message))
                raise ModelCatalogError("Model Catalog error trying to abort transaction")

    def abort(self, tx):
        try:
            self._delete_temporary_tx_documents()
        finally:
            self.reset_tx_state(tx)

    def tpc_begin(self, transaction):
        pass

    def commit(self, transaction):
        pass

    def tpc_vote(self, transaction):
        # Check connection to SOLR
        if not self.ping_index():
            raise ModelCatalogUnavailableError()

    def tpc_finish(self, transaction):
        try:
            tx_state = self._get_tx_state(transaction)
            if tx_state:
                updates = tx_state.get_updates_to_finish_transaction()
                dirty_tx = tx_state.are_there_indexed_updates()
                try:
                    self.model_index.process_model_updates(updates)
                    self._delete_temporary_tx_documents()
                    # @TODO TEMP LOGGING
                    log.warn("COMMIT_METRIC: {0}. MID-TX COMMITS? {1}".format(tx_state.commits_metric, dirty_tx))
                except Exception as e:
                    log.exception("Exception in tcp_finish: {0} / {1}".format(e, e.message))
                    self.abort(transaction)
                    raise
        finally:
            self.reset_tx_state(transaction)

    def tpc_abort(self, transaction):
        pass

    def sortKey(self):
        return "model_catalog"

    def savepoint(self, optimistic=False):
        return NoRollbackSavepoint(self)


class ModelCatalog(object):
    """ This class provides Solr Clients """

    def __init__(self, solr_url):
        # module modelindex registers the indexer and searcher constructor factories in ZCA
        #
        self.solr_url = solr_url
        """
        Each Zope thread has its own solr indexer and reader. Model catalog clients are identified 
        by the thread's zodb connection id
        """

    def get_client(self, context):
        """
        Retrieves/creates the solr client for the zope thread that is trying to access solr
        """
        zodb_conn = context.get("_p_jar")

        catalog_client = None

        # context is not a persistent object. Create a temp client in a volatile variable.
        # Volatile variables are not shared across threads, so each thread will have its own client
        #
        if zodb_conn is None:
            if not hasattr(self, "_v_temp_model_catalog_client"):
                self._v_temp_model_catalog_client = ModelCatalogClient(self.solr_url)
            catalog_client = self._v_temp_model_catalog_client
        else:
            #
            # context is a persistent object. Create/retrieve the catalog client
            # from the zodb connection object. We store the client in the zodb
            # connection object so we are certain that each zope thread has its own
            catalog_client = getattr(zodb_conn, 'model_catalog_client', None)
            if catalog_client is None:
                zodb_conn.model_catalog_client = ModelCatalogClient(self.solr_url)
                catalog_client = zodb_conn.model_catalog_client

        return catalog_client


    def catalog_object(self, obj, idxs=None):
        """ """
        catalog_client = self.get_client(obj)
        catalog_client.catalog_object(obj, idxs)

    def uncatalog_object(self, obj):
        """ """
        catalog_client = self.get_client(obj)
        catalog_client.uncatalog_object(obj)


def get_solr_config():
    config = getGlobalConfiguration()
    return config.get('solr-servers', 'http://localhost:8984')


def register_model_catalog():
    """
    Register the model catalog as an utility
    To get the utility we will use this code:
        >>> from Products.Zuul.catalog.interfaces import IModelCatalog
        >>> from zope.component import getUtility
        >>> getUtility(IModelCatalog)
    """
    model_catalog = ModelCatalog(get_solr_config())
    getGlobalSiteManager().registerUtility(model_catalog, IModelCatalog)


register_model_catalog()


