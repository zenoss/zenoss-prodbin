
import logging
import transaction
import zope.component

from interfaces import IModelCatalog
from collections import defaultdict
from Products.ZenModel.Software import Software
from Products.ZenModel.OperatingSystem import OperatingSystem
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.Zuul.catalog.interfaces import IIndexableWrapper
from transaction.interfaces import IDataManager
from zenoss.modelindex import indexed, index
from zenoss.modelindex.field_types import StringFieldType, \
     ListOfStringsFieldType, IntFieldType, DictAsStringsFieldType, LongFieldType
from zenoss.modelindex.constants import INDEX_UNIQUE_FIELD as UID
from zenoss.modelindex.exceptions import IndexException
from zenoss.modelindex.indexer import IndexTask, INDEX, UNINDEX
from zope.component import getGlobalSiteManager, getUtility
from zope.interface import implements

log = logging.getLogger("model_catalog")

#logging.getLogger("requests").setLevel(logging.ERROR) # requests can be pretty chatty 


class ModelCatalogUnavailableError(Exception):
    def __init__(self, message = "Model Catalog not available"):
        super(ModelCatalogUnavailableError, self).__init__(message)


class ModelCatalogClient(object):

    def __init__(self, solr_url):
        # @TODO Should we collapse indexer and searcher in a unique connection?
        # Since we have a client per thread we wont need search and index at the same time
        self.indexer = zope.component.createObject('ModelIndexer', solr_url)
        self.searcher = zope.component.createObject('ModelSearcher', solr_url)
        self.data_manager = ModelCatalogDataManager(self)

    def _get_forbidden_classes(self):
        return (Software, OperatingSystem)

    def is_model_catalog_enabled(self):
        return self.indexer is not None

    def getIndexes(): # Do we need to implement it?
        pass

    def catalog_object(self, obj, idxs=None):
        if self.is_model_catalog_enabled() and \
           not isinstance(obj, self._get_forbidden_classes()):
            try:
                self.data_manager.add_task(IndexTask(obj, op=INDEX, idxs=idxs))
            except IndexException as e:
                log.error("EXCEPTION {0} {1}".format(e, e.message))
                raise ModelCatalogUnavailableError()

    def uncatalog_object(self, obj):
        if self.is_model_catalog_enabled() and \
           not isinstance(obj, self._get_forbidden_classes()):
            try:
                self.data_manager.add_task(IndexTask(obj, op=UNINDEX))
            except IndexException as e:
                log.error("EXCEPTION {0} {1}".format(e, e.message))
                raise ModelCatalogUnavailableError()


class NoRollbackSavepoint(object):
    def __init__(self, datamanager):
        self.datamanager = datamanager

    def rollback(self):
        pass

class ModelCatalogDataManager(object):

    implements(IDataManager)

    def __init__(self, model_catalog):
        self.model_catalog = model_catalog
        self.updated_objects_per_transaction = defaultdict(dict) # {transaction_id: {object_uid: [list of index tasks]  }}
        # @TODO ^^ Make that an OOBTREE to avoid concurrency issues? I dont think we need it since we have one per thread

    def reset_tx_state(self, tx):
        tx_id = id(tx)
        if tx_id in self.updated_objects_per_transaction:
            del self.updated_objects_per_transaction[tx_id]

    def add_task(self, task):
        tx = transaction.get()
        tx_id = id(tx)
        if tx_id not in self.updated_objects_per_transaction:
            tx.join(self)

        # @TODO For the time being we only have two index operations INDEX and UNINDEX
        # Once we are able to index only certain indexes and use solr
        # atomic updates this will become more complex in order to send as few requests to solr
        # as possible
        #
        # we overwrite any previous operation since we can only index/unindex the whole object
        #
        self.updated_objects_per_transaction[tx_id][task.uid] = task


    def abort(self, tx):
        try:
            # @TODO add close to indexer and searcher
            """c = self._connection
            if c is not None:
                self._connection = None
                c.close()
            """
            pass
        finally:
            self.reset_tx_state(tx)

    def tpc_begin(self, transaction):
        pass

    def commit(self, transaction):
        pass

    def tpc_vote(self, transaction):
        # Check connection to SOLR
        if not self.model_catalog.indexer.ping():
            raise ModelCatalogUnavailableError()

    def tpc_finish(self, transaction):
        try:
            tx_id = id(transaction)
            tx_objects = self.updated_objects_per_transaction[tx_id]

            tasks = tx_objects.values()
            try:
                self.model_catalog.indexer.process_tasks(tasks)
            except:
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
        Retrieves/creates the solr client for the zope thread that is trying to index/unindex an object
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


def register_model_catalog():
    """
    Register the model catalog as an utility
    To get the utility we will use this code:
        >>> from Products.Zuul.catalog.interfaces import IModelCatalog
        >>> from zope.component import getUtility
        >>> getUtility(IModelCatalog)
    """
    config = getGlobalConfiguration()
    solr_servers = config.get('solr-servers', 'http://localhost:8984')
    model_catalog = ModelCatalog(solr_servers)
    getGlobalSiteManager().registerUtility(model_catalog, IModelCatalog)


register_model_catalog()


