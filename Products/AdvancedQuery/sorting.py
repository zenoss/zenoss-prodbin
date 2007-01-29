# Copyright (C) 2003-2006 by Dr. Dieter Maurer, Eichendorffstr. 23, D-66386 St. Ingbert, Germany
#       $Id: sorting.py,v 1.3 2006/11/09 19:27:33 dieter Exp $
'''Auxiliary sorting module'''

from BTrees.IIBTree import difference, IISet, IITreeSet
from BTrees.OOBTree import OOBTree

from AdvancedQuery import _notPassed, intersection

def sort(seq, sortSpecs, withSortValue):
  '''sort 'IISet/IITreeSet' *seq* according to *sortSpec*.

  *sortSpecs* is a sequence of sort specs.

  The result has '__getitem__' and '__len__' methods.
  '__getitem__' must be called with sucessive integers, starting
  with '0'. This is sufficient for 'LazyMap'.

  If *withSortValue*, '__getitem__' returns triple
  *sortValue*, 'None', *documentId*, otherwise *documentId*.
  '''
  n = len(seq)
  if not withSortValue and (not sortSpecs or n <= 1): return seq
  return _SortAccess(n, _sort(seq, sortSpecs, withSortValue))


class _SortAccess:
  '''auxiliary wrapper class (to provide '__getattr__' and '__len__').'''
  def __init__(self, len, generator):
    self._index = 0
    self._len = len
    self._iter = generator

  def __getitem__(self,index):
    if index >= self._len: raise IndexError
    if index != self._index:
      raise SystemError('unconsequtive access')
    self._index += 1
    s = self._iter.next()
    if isinstance(s, tuple):
      # with sort values
      sv, did = s
      s = None, sv, did
    return s

  def __len__(self): return self._len


def _sort(seq, sortSpecs, withSortValues):
  # Note: "set" is an "IISet" or "IITreeSet"
  ns = len(seq)
  if ns == 1 and not withSortValues: yield seq.keys()[0]; return

  if not sortSpecs:
    wrap = withSortValues and (lambda did, e=(): (e, did)) or (lambda did: did)
    for s in seq.keys(): yield wrap(s)
    return

  sortSpecs = sortSpecs[:]
  sortSpec = sortSpecs.pop(0)
  for value, subseq in sortSpec.group(seq):
    subseq = _sort(subseq, sortSpecs, withSortValues)
    if withSortValues:
      for sv, did in subseq: yield (value,) + sv, did
    else:
      for did in subseq: yield did


class Sorter(object):
  '''abstract base class to handle sorting with respect to one sort level.'''
  def group(self, seq):
    '''group *seq* (a set) generating pairs (*value*, *subseq*).

    All elements in *subseq* (a set) have *value* as sort value on this level.
    The union of all *subseq* gives *seq*.

    Elements not sorted on this level go into the last generated
    pair with 'None' as value.
    '''
    raise NotImplementedError


class IndexSorter(Sorter):
  '''sorting with respect to an index.'''
  def __init__(self, sortIndex, sortReverse):
    self._sortIndex = sortIndex; self._sortReverse = sortReverse

  def group(self, seq):
    sortIndex = self._sortIndex; sortReverse = self._sortReverse
    ns = len(seq); ni = len(sortIndex)
    if ns >= 0.1 * ni:
      # result large compared to index -- sort via index
      handled = IISet(); hn = 0
      _load = getattr(sortIndex, '_load', None)
      if _load is None:
        # not an optimized index
        items = sortIndex.items()
        
        _load = lambda (x1, x2): x2
        if sortReverse: items.reverse()
      elif sortReverse:
        gRO = getattr(sortIndex, 'getReverseOrder', None)
        items = gRO and gRO()
        if items is None:
          items = list(sortIndex._index.keys()); items.reverse()
      else: items = sortIndex._index.keys()
      for i in items:
        ids = intersection(seq, _load(i))
        if ids:
          handled.update(ids); hn += len(ids)
          yield i, ids
      if hn != len(seq): yield None, difference(seq, handled)
    else:
      # result relatively small -- sort via result
      keyFor = sortIndex.keyForDocument; m = OOBTree()
      noValue = IITreeSet()
      for doc in seq.keys():
        try: k = keyFor(doc)
        except KeyError: noValue.insert(doc); continue
        l = m.get(k)
        if l is None: l = m[k] = IITreeSet()
        l.insert(doc)
      items = m.items()
      if sortReverse: items = list(items); items.reverse()
      for i in items: yield i
      if noValue: yield None, noValue


def normSortSpecs(specs, withSortValue, cat):
  '''normalize sort specs *specs* and *withSortValue*.

  *specs* is a sequence of sort specifications.
  A sort specification is either a 'RankSpec', an index name
  or a pair index name + sorting order ('asc'/'desc').

  If 'withSortValue' is '_notPassed', then it is set to 'True',
  is *specs* contains a 'RankSpec', otherwise to 'False'.
  '''
  l= []; withValue = False
  for s in specs:
    if hasattr(s, '_prepare'): s = s._prepare(cat); withValue = True
    else:
      if isinstance(s, tuple): si,so= s
      else: si=s; so= 'asc'
      i= cat.indexes[si]
      # ensure, the index supports sorting
      if not hasattr(i,'documentToKeyMap'):
        raise ValueError,'Index not adequate for sorting: %s' % si
      # check whether we should reverse the order
      so= so.lower()
      if so in ('asc', 'ascending'): sr= 0
      elif so in ('desc', 'descending', 'reverse'): sr= 1
      s = IndexSorter(i, sr)
    l.append(s)
  if withSortValue is _notPassed: withSortValue = withValue
  return l, withSortValue
