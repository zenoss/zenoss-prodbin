#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################
__doc__='''
This migration script integrates support for the ManagableIndex and
AdvancedQuery Products by removing old indexes and replacing them with
ManagableFieldIndex indices.
''' 

__version__ = "$Revision$"[11:-2]
        
import transaction
from Products.ManagableIndex import FieldIndex
from Products.ManagableIndex import KeywordIndex_scalable as KeywordIndex
from Products.ZenModel.SearchUtils import makeFieldIndex
from Products.ZenModel.SearchUtils import makeKeywordIndex

import Migrate

allCatalogs = {
    'Devices': {
        'componentSearch': ['meta_type', 'monitored'],
        'deviceSearch': ['id', 'summary'],
    },
    'Services': {
        'serviceSearch': ['serviceKeys'],
    },
    'Manufacturers': {
        'productSearch': ['productKeys'],
    },
    'Mibs': {
        'mibSearch': ['id', 'oid', 'summary'],
    },
    'Events': {
        'eventClassSearch': ['eventClassKey'],
    },
    'Networks': {
        'ipSearch': ['id'],
    },
}

class AdvancedQuery(Migrate.Step):
    version = 23.0

    def cutover(self, dmd):
        # create a new index
        for section, catalogNames in allCatalogs.items():
            # see which king of index we need to create
            if section in ['Services', 'Manufacturers', 'Mibs']:
                makeIndex = makeKeywordIndex
            else:
                makeIndex = makeFieldIndex
            for catalogName, indexNames in catalogNames.items():
                zcat = getattr(dmd.getDmdRoot(section), catalogName)
                cat = zcat._catalog
                for indexName in indexNames:
                    if (catalogName == 'componentSearch' and 
                        indexName == 'monitored'):
                        # the monitored index contains bools, so we're not
                        # going to mess with it
                        continue
                    # get rid of the old index
                    cat.delIndex(indexName)
                    # add the new one
                    cat.addIndex(indexName, makeIndex(indexName))
                    transaction.commit()
            # reindex the sections
            dmd.getDmdRoot(section).reIndex()
            transaction.commit()

AdvancedQuery()
