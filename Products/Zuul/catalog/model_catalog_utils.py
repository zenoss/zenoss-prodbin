
import Globals

import argparse
import zope.component

from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.Zuul.catalog.model_catalog import get_solr_config
from zenoss.modelindex.model_index import SearchParams
from zenoss.modelindex.constants import INDEX_UNIQUE_FIELD as UID, ZENOSS_MODEL_COLLECTION_NAME


class ModelCatalogUtils(object):

    def __init__(self):
        self.model_index = zope.component.createObject('ModelIndex', get_solr_config())

    def unindex_by_uid(self, uid):
        query={UID: uid}
        search_params=SearchParams(query=query)
        self.model_index.unindex_search(search_params, collection=ZENOSS_MODEL_COLLECTION_NAME)


def main(options):
    utils = ModelCatalogUtils()
    utils.unindex_by_uid(options.uid)


def parse_options():
    parser = argparse.ArgumentParser(description="Model Catalog hacking tool", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("action", type=str, choices=['unindex'], help="Action to perform")
    parser.add_argument("-u", "--uid", dest="uid", type=str, help="Full path of the zodb object to operate on")
    return parser.parse_args()


if __name__ == "__main__":
    import sys
    options = parse_options()
    print("{} called with options {}\n".format(sys.argv[0], options))
    sys.argv = sys.argv[:1] # clean up the cli args so ZenScriptBase does not bark
    main(options)