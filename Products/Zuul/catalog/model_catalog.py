
import logging
import zope.component

from interfaces import IModelCatalog
from zenoss.modelindex import indexed, index
from zenoss.modelindex.field_types import StringFieldType, \
     ListOfStringsFieldType, IntFieldType, DictAsStringsFieldType, LongFieldType
from zenoss.modelindex.constants import INDEX_UNIQUE_FIELD as UID
from zenoss.modelindex.exceptions import IndexException
from Products.ZenModel.Software import Software
from Products.ZenModel.OperatingSystem import OperatingSystem
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.Zuul.catalog.interfaces import IIndexableWrapper
from zope.component import getGlobalSiteManager
from zope.interface import implements

log = logging.getLogger("model_catalog")

#logging.getLogger("requests").setLevel(logging.ERROR) # requests can be pretty chatty 


class ModelCatalogUnavailableError(Exception):
    def __init__(self, message = "Model Catalog not available"):
        super(ModelCatalogUnavailableError, self).__init__(message)


class ModelCatalog(object):
    """ """

    def __init__(self, solr_url):
        # module modelindex registers the indexer and searcher constructor factories in ZCA
        #
        self.indexer = zope.component.createObject('ModelIndexer', solr_url)
        self.searcher = zope.component.createObject('ModelSearcher', solr_url)

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
                self.indexer.index(obj, idxs)
            except IndexException as e:
                log.error("EXCEPTION {0} {1}".format(e, e.message))
                raise ModelCatalogUnavailableError()

    def uncatalog_object(self, obj):
        if self.is_model_catalog_enabled() and \
           not isinstance(obj, self._get_forbidden_classes()):
            try:
                self.indexer.unindex(obj)
            except IndexException as e:
                log.error("EXCEPTION {0} {1}".format(e, e.message))
                raise ModelCatalogUnavailableError()

    def unindex_object_from_paths(self, obj, paths):
        # Remove paths from obj's paths
        self.catalog_object(obj)  # @TODO this is very inefficient. REVISIT

    def index_object_under_paths(self, obj, paths):
        # Add paths to obj's paths
        self.catalog_object(obj)  # @TODO this is very inefficient. REVISIT


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



