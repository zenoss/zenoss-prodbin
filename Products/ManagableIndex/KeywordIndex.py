# Copyright (C) 2003 by Dr. Dieter Maurer, Eichendorffstr. 23, D-66386 St. Ingbert, Germany
# see "LICENSE.txt" for details
#       $Id: KeywordIndex.py,v 1.8 2006/05/17 19:53:07 dieter Exp $
'''Managable KeywordIndex.'''

from sys import maxint

from BTrees.OOBTree import difference, OOSet, union, OOTreeSet

from ManagableIndex import ManagableIndex, addForm


class KeywordIndex(ManagableIndex):
  '''a managable 'KeywordIndex'.'''
  meta_type= 'Managable KeywordIndex'

  Combiners= ManagableIndex.Combiners + ('union',)
  CombineType= Combiners[-1]

  def _createDefaultValueProvider(self):
    ManagableIndex._createDefaultValueProvider(self)
    # add (value) normalizer to let it behave identical to
    # a standard Zope KeywordIndex
    vp= self.objectValues()[0]
    setattr(vp, vp.NormalizerProperty, 'python: hasattr(value,"capitalize") and (value,) or value')

  def _indexValue(self,documentId,val,threshold):
    if not threshold: threshold= maxint
    n= i= 0; T= get_transaction()
    for v in val.keys():
      self._insert(v,documentId)
      n+=1; i+=1
      if i == threshold: T.commit(1); i= 0
    return n

  def _unindexValue(self,documentId,val):
    for v in val.keys():
      self._remove(v,documentId)

  def _update(self,documentId,val,oldval,threshold):
    add= difference(val,oldval)
    rem= difference(oldval,val)
    if add: self._indexValue(documentId,add,threshold)
    if rem: self._unindexValue(documentId,rem)
    self._updateOldval(oldval, val, add, rem)
    return len(add),

  def _updateOldval(self, oldval, newval, add, rem):
    # optimize transaction size by not writing _unindex bucket
    oldval.clear(); oldval.update(newval)

  def _equalValues(self,val1,val2):
    if val1 == val2: return 1
    if val1 is None or val2 is None: return 0
    return tuple(val1.keys()) == tuple(val2.keys())

  def _combine_union(self,values,object):
    if not values: return
    set= None
    for v in values:
      sv= self._standardizeValue(v,object)
      if not sv: continue
      set= union(set,sv)
    return set

  _SETTYPE = OOSet

  def _standardizeValue(self,value,object):
    '''convert to a set of standardized terms.'''
    if not value: return
    set= self._SETTYPE([st for st in [self._standardizeTerm(t,object) for t in value] if st is not None])
    return set or None

  # filtering support
  supportFiltering = True

  def _makeFilter(self, pred):
    '''a document filter 'did -> True/False' checking term predicate *pred*.'''
    def check(did):
      dv = self._unindex.get(did)
      if dv is None: return False
      for t in dv.keys():
        if pred(t): return True
      return False
    return check

def addKeywordIndexForm(self):
  '''add KeywordIndex form.'''
  return addForm.__of__(self)(
    type= KeywordIndex.meta_type,
    description= '''A KeywordIndex indexes an object under a set of terms.''',
    action= 'addIndex',
    )

class KeywordIndex_scalable(KeywordIndex):
  '''a Keyword index that can efficiently handle huge keyword sets per object.'''
  _SETTYPE = OOTreeSet
  meta_type = 'Managable KeywordIndex (scalable)'

  def _updateOldval(self, oldval, newval, add, rem):
    for t in rem: oldval.remove(t)
    oldval.update(add)

def addKeywordIndex_scalableForm(self):
  '''add KeywordIndex form.'''
  return addForm.__of__(self)(
    type= KeywordIndex_scalable.meta_type,
    description= '''A KeywordIndex (scalable) indexes an object under a (potentially huge) set of terms.''',
    action= 'addIndex',
    )

try:
  import transaction # ZODB 3.4 (Zope 2.8)
  def get_transaction(): return transaction
except ImportError: pass # pre ZODB 3.4
