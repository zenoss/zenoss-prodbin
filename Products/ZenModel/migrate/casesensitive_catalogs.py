#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################
__doc__='''
This migration script removes case insensitivity from the catalogs that was
configured with the move to AdvancedQuery.
''' 

__version__ = "$Revision$"[11:-2]
        
from Products.ZCatalog.Catalog import CatalogError

from Products.ZenUtils.Search import makeFieldIndex
from Products.ZenUtils.Search import makeKeywordIndex

import Migrate

from advanced_query import allCatalogs

class CaseSensitive(Migrate.Step):

    version = Migrate.Version(1, 0, 0)

    def cutover(self, dmd):
        # initialize our index tracker, in case catalogNames is empty
        indexed = {}
        for section, catalogNames in allCatalogs.items():
            # see which kind of index we need to create
            if section in ['Services', 'Manufacturers', 'Mibs']:
                makeIndex = makeKeywordIndex
            else:
                makeIndex = makeFieldIndex
            for catalogName, indexNames in catalogNames.items():
                # we'll use a dict to keep track of whether this catalog will
                # need reindexing or not
                indexed = {}
                zcat = getattr(dmd.getDmdRoot(section), catalogName)
                cat = zcat._catalog
                # check the indices for a pre-normalizer attribute
                for indexName in indexNames:
                    idx = cat.getIndex(indexName)
                    if (hasattr(idx, 'PrenormalizeTerm') and 
                        idx.PrenormalizeTerm == 'value/lower'):
                        idx.PrenormalizeTerm = ''
                        indexed[catalogName] = True
            # reindex the current section
            if True in indexed.values():
                dmd.getDmdRoot(section).reIndex()

CaseSensitive()
