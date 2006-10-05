#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""SearchUtils

Utilities to help build zcatalog indexes

$Id: SearchUtils.py,v 1.3 2003/12/22 16:52:43 edahl Exp $"""

__version__ = "$Revision: 1.3 $"[11:-2]

from Products.ManagableIndex import FieldIndex, KeywordIndex

def makeFieldIndex(indexName):
    index = FieldIndex(indexName)
    index.PrenormalizeTerm = 'value/lower'
    index.TermType = 'ustring'
    return index

def makeKeywordIndex(indexName):
    index = KeywordIndex(indexName)
    index.PrenormalizeTerm = 'value/lower'
    index.TermType = 'ustring'
    index.TermTypeExtra = 'latin-1'
    return index

