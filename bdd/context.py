
import Globals
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.Zuul.catalog.interfaces import IModelCatalogTool

from utils.zodb_helper import ZodbHelper
from utils.model_catalog_helper import ModelCatalogHelper

"""
BDD context objects that are available in each test step
"""

class ZodbContext(object):
    """
    BDD context with a connection to zodb and a reference
    to a zodb helper
    """
    def __init__(self):
        self.dmd = ZenScriptBase(connect=True).dmd
        self.zodb_helper = ZodbHelper(self.dmd)


class ModelCatalogContext(ZodbContext):
    """
    BDD context with a reference to a model_catalog client and
    to a helper class
    """
    def __init__(self):
        super(ModelCatalogContext, self).__init__()
        self.model_catalog = IModelCatalogTool(self.dmd)
        self.model_catalog_helper = ModelCatalogHelper(self.model_catalog)
        self.solr_client = self.model_catalog.model_catalog_client._data_manager.model_index
