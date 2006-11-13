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

from Products.ZenUtils.Search import makeCaseSensitiveFieldIndex
from Products.ZenUtils.Search import makeCaseSensitiveKeywordIndex
from Products.ZenUtils.Search import makeCaseInsensitiveFieldIndex
from Products.ZenUtils.Search import makeCaseInsensitiveKeywordIndex

import Migrate

from advanced_query import allCatalogs, keywordCatalogs

caseSensitiveCatalogs = [
    'componentSearch',
    'eventClassSearch',
    'productSearch',
    'serviceSearch',
    ]

class CaseSensitive(Migrate.Step):

    version = Migrate.Version(1, 0, 0)

    def cutover(self, dmd):
        # initialize our index tracker, in case catalogNames is empty
        indexed = {}
        for section, catalogNames in allCatalogs.items():
            for catalogName, indexNames in catalogNames.items():
                # we'll use a dict to keep track of whether this catalog will
                # need reindexing or not
                indexed = {}
                zcat = getattr(dmd.getDmdRoot(section), catalogName)
                cat = zcat._catalog
                # check to see if this needs to be a case-sensitive index
                if catalogName in caseSensitiveCatalogs:
                    prenormalizer = ''
                    # check to see if it needs to be a keyword index
                    if section in keywordCatalogs:
                        makeIndex = makeCaseSensitiveKeywordIndex
                    else:
                        makeIndex = makeCaseSensitiveFieldIndex
                else:
                    prenormalizer = 'value/lower'
                    # check to see if it needs to be a keyword index
                    if section in keywordCatalogs:
                        makeIndex = makeCaseInsensitiveKeywordIndex
                    else:
                        makeIndex = makeCaseInsensitiveFieldIndex
                # check the indices for a pre-normalizer attribute
                for indexName in indexNames:
                    idx = cat.getIndex(indexName)
                    if (hasattr(idx, 'PrenormalizeTerm') and 
                        idx.PrenormalizeTerm != prenormalizer):
                        idx.PrenormalizeTerm = prenormalizer
                        indexed[catalogName] = True
            # reindex the current section
            if True in indexed.values():
                dmd.getDmdRoot(section).reIndex()

CaseSensitive()
