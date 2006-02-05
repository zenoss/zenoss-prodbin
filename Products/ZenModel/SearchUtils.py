#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""SearchUtils

Utilities to help build zcatalog indexes

$Id: SearchUtils.py,v 1.3 2003/12/22 16:52:43 edahl Exp $"""

__version__ = "$Revision: 1.3 $"[11:-2]


from Products.ZCTextIndex.PipelineFactory import element_factory
from Products.ZCTextIndex.ZCTextIndex import manage_addLexicon


class __R:pass

def makeConfmonLexicon(zcat):
    
    ws=__R()
    ws.name='Confmon splitter'
    ws.group='Word Splitter'
    cn=__R()
    cn.name='Case Normalizer'
    cn.group='Case Normalizer'
    manage_addLexicon(zcat, 'myLexicon', elements=(cn, ws,))


def makeIndexExtraParams(indexName):
    idx=__R()
    idx.index_type='Okapi BM25 Rank'
    idx.lexicon_id='myLexicon'
    idx.doc_attr=indexName
    return idx


class ConfmonSplitter:
    """Extremely simple spliitter for ZCTextIndex that uses split to break
    indexing targets into "words".  We don't want to split thing like:

    ipaddresses -> 1.2.3.4
    macaddresses -> aa:bb:cc:11:00:11
    fqdn -> www.zentinel.net
    Wacky model names -> 12/xyz
    """
    import re
    #rx = re.compile(r"[\w.]+")
    rxGlob = re.compile(r"[\w.-]+[\w*?]*") # See globToWordIds() above

    def process(self, lst):
        result = []
        for s in lst:
            #result += self.rx.findall(s)
            result += str(s).split()
        return result

    def processGlob(self, lst):
        result = []
        for s in lst:
            result += self.rxGlob.findall(s)
            #result += str(s).split()
        return result

if not 'Confmon splitter' in element_factory.getFactoryNames('Word Splitter'):
    element_factory.registerFactory('Word Splitter','Confmon splitter',
                                     ConfmonSplitter)

