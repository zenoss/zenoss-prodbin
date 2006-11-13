#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""Search

Utilities to help build zcatalog indexes
"""

__version__ = "$Revision: 1.3 $"[11:-2]

from Products.ManagableIndex import FieldIndex, KeywordIndex

def makeCaseInsensitiveFieldIndex(indexName):
    index = FieldIndex(indexName)
    index.PrenormalizeTerm = 'value/lower'
    index.TermType = 'ustring'
    return index

def makeCaseInsensitiveKeywordIndex(indexName):
    index = KeywordIndex(indexName)
    index.PrenormalizeTerm = 'value/lower'
    index.TermType = 'ustring'
    index.TermTypeExtra = 'latin-1'
    return index

def makeCaseSensitiveKeywordIndex(indexName):
    index = KeywordIndex(indexName)
    index.TermType = 'ustring'
    index.TermTypeExtra = 'latin-1'
    return index

def makeCaseSensitiveFieldIndex(indexName):
    index = FieldIndex(indexName)
    index.TermType = 'ustring'
    return index

def makeFieldIndex(indexName):
    return makeCaseInsensitiveFieldIndex(indexName)

def makeKeywordIndex(indexName):
    return makeCaseInsensitiveKeywordIndex(indexName)

