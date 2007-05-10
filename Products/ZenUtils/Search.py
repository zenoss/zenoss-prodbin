###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__="""Search

Utilities to help build zcatalog indexes
"""

__version__ = "$Revision: 1.3 $"[11:-2]

from Products.ManagableIndex import FieldIndex, KeywordIndex, PathIndex

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

def makePathIndex(indexName):
    return PathIndex(indexName)
