# Copyright (C) 2004 by Dr. Dieter Maurer, Eichendorffstr. 23, D-66386 St. Ingbert, Germany
# see "LICENSE.txt" for details
#       $Id: KeywordIndex.py,v 1.4 2004/07/30 11:12:09 dieter Exp $
'''Managable WordIndex.

A word index lies between a 'KeywordIndex' and a 'TextIndex'.

Like a 'TextIndex', it uses a 'Lexicon' to split values into
a sequence of words, stores integer word ids in its index
and does not support range queries.
Like a 'KeywordIndex', it indexes an object under a sequence of words --
no near or phrase queries and no relevancy ranking.
Due to these restrictions, a 'WordIndex' is very efficient with respect
to transaction and load size.

The motivation to implement a
'WordIndex' came from my observation, that almost all our ZEO loads
above 100ms were caused by loading large word frequency
IOBuckets used by 'TextIndex'es for relevancy ranking -- a feature
we do not need and use. Many of these loads transfered buckets
of several 10 kB and a considerable portion of them took more
than a second. As word frequency information is necessary for
each document in a hit, you can imagine how fast our queries
were.

On the other hand, a 'WordIndex' is only useful when you
use a flexible query framework, such as e.g. 'AdvancedQuery'
or 'CatalogQuery'.
The standard 'ZCatalog' framework is too weak as it does not
allow to have several subqueries against the same index
in a query. Thats the reason why 'TextIndex'es come with
their own query parser. I live in Germany and therefore
the standard query parser is useless for us (we use 'und', 'oder',
'nicht' instead of 'and', 'or' and 'not') and I have 'AdvancedQuery' --
thus I did not care to give the new 'WordIndex' a query parser.
You could easily provide one -- should you feel a need for it.
'''

from Acquisition import aq_base

from BTrees.IIBTree import IITreeSet, difference

from ManagableIndex import addForm, ManagableIndex
from KeywordIndex import KeywordIndex

class WordIndex(KeywordIndex):
  '''a managable 'WordIndex'.'''
  meta_type = 'Managable WordIndex'

  query_options = ('operator', 'match', 'isearch')
  TermType = 'integer'

  _properties = ManagableIndex._properties[:1] + (
    {'id':'PrenormalizeTerm', 'type':'string', 'mode':'w',
     'label':'Match normalizer: applied to match patterns -- this should match the lexicons normalization',},
    {'id':'Lexicon', 'type':'string', 'mode':'w',
     'label':'Lexicon id of a ZCTextIndex like lexicon (resolved with respect to the catalog) -- clear+reindex after change',},
    )
  Lexicon = ''

  _createDefaultValueProvider = ManagableIndex._createDefaultValueProvider

  # override for better readability
  def getEntryForObject(self,documentId, default= None):
    '''Information for *documentId*.'''
    info= self._unindex.get(documentId)
    if info is None: return default
    lexicon = self._getLexicon()
    l = [lexicon.get_word(wid) for wid in info.keys()]; l.sort()
    return repr(l)
  
  # overrides: we could use the corresponding 'KeywordIndex' definitions
  # but as the word sets tend to be much larger,
  # we use definitions which are more efficient for large sets
  def _update(self,documentId,val,oldval,threshold):
    add= difference(val,oldval)
    rem= difference(oldval,val)
    if add: self._indexValue(documentId,add,threshold)
    if rem: self._unindexValue(documentId,rem)
    # optimize transaction size by not writing _unindex bucket
    if len(rem) < 100:
      for x in rem: oldval.remove(x) # sad that we do not have a mass remove
      oldval.update(add)
    else: oldval.clear(); oldval.update(val)
    return len(add),

## the KeywordIndex implementation is more efficient
##  def _equalValues(self, val1, val2):
##    if val1 == val2: return True
##    if val1 is None or val2 is None: return False
##    it1 = val1.keys(); it2 = val2.keys(); i = 0
##    while True:
##      k1 = k2 = self
##      try: k1 = it1[i]
##      except IndexError: pass
##      try: k2 = it2[i]
##      except IndexError: pass
##      if k1 != k2: return False
##      if k2 is self: return True
##      i+= 1

  def _combine_union(self, values, object):
    if not values: return
    set= None
    for v in values:
      sv= self._standardizeValue_(v, object)
      if not sv: continue
      if set is None: set = IITreeSet(sv)
      else: set.update(sv)
    return set

  def _standardizeValue(self, value, object):
    '''convert to an IITreeSet of standardized terms.'''
    terms = self._standardizeValue_(self, value, object)
    if terms: return IITreeSet(terms)

  ## essential work delegated to lexicon
  def _standardizeValue_(self, value, object):
    '''convert to a sequence of standardized terms.'''
    if not value: return
    lexicon = self._getLexicon()
    # we assume some type of "Products.ZCTextIndex.Lexicon.Lexicon" instance
    return lexicon.sourceToWordIds(value)

  def _normalize(self, value, object):
    '''convert term *value* to word id.'''
    if isinstance(value, int): return value # already normalized
    # ATT: returns 0, when the word is unknown
    # This implies that searches for unknown words cannot get matches
    wids = self._getLexicon().termToWordIds(value)
    if len(wids) != 1:
      raise ValueError('Word index %s can only handle word queries: %s'
                       % (self.id, value)
                       )
    return wids[0]
    
  def _getLexicon(self):
    # resolve with respect to catalog -- this is nasty but necessary
    # to avoid acquisition from the internal "_catalog".
    obj = self
    while not hasattr(aq_base(obj), 'Indexes'): obj = obj.aq_inner.aq_parent
    lexicon = getattr(obj, self.Lexicon, None)
    if lexicon is None:
      raise ValueError('Lexicon not found: ' + self.Lexicon)
    return lexicon

  _matchType = 'asis'
  def _getMatchIndex(self):
    # ATT: internal knowledge about ZCTextIndex.Lexicon.Lexicon!
    return self._getLexicon()._wids



def addWordIndexForm(self):
  '''add KeywordIndex form.'''
  return addForm.__of__(self)(
    type= WordIndex.meta_type,
    description= '''A WordIndex indexes an object under a set of word ids determined via a 'ZCTextIndex' like lexicon.''',
    action= 'addIndex',
    )
    
