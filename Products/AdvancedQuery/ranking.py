# Copyright (C) 2003-2006 by Dr. Dieter Maurer, Eichendorffstr. 23, D-66386 St. Ingbert, Germany
#       $Id: ranking.py,v 1.1 2006/06/25 19:11:24 dieter Exp $
'''Ranking Support.'''

from BTrees.IIBTree import difference

from AdvancedQuery import _BaseQuery, LiteralResultSet, And, intersection
from sorting import Sorter
from eval import _eval


class RankSpec(object):
  '''abstract ranking specification.'''
  def _prepare(self, cat):
    '''return a sorter using *cat*.'''
    raise NotImplementedError

class _Ranker(Sorter):
  '''a sorter base class used for ranking.'''
  def __init__(self, spec, cat):
    self._spec = spec; self._cat = cat

  def group(self, seq):
    normalize = self._normalize
    for rank, subseq in self._group(seq):
      yield normalize(rank), subseq

  # implemented by derived classes
  def _group(self, seq):
    raise NotImplementedError

  # may be overridden by derived classes
  def _normalize(self, rank): return rank


class _RankByQueries(RankSpec):
  '''Ranking specification base class for rankings based on a sequence of (*query*, *value*) pairs.

  All values must be non negative numbers.
  '''
  # defined by derived classes
  _RankerClass = None

  def __init__(self, *specs):
    '''each spec is a pair *query*, *value*.'''
    l = []; sum = 0
    for q,v in specs:
      if not isinstance(q, _BaseQuery):
        raise TypeError('Query must be an AdvancedQuery')
      if not isinstance(v, (int, float, long)):
        raise TypeError('Query value must be a float')
      if v < 0: raise ValueError('Query value must not be negative')
      if not v: continue
      l.append((v,q)); sum += v
    l.sort()
    self._specs = l; self._sum = sum

  def getQueryValueSum(self): return self._sum
  def _getValueQuerySequence(self): return self._specs

  def _prepare(self, cat):
    return self._RankerClass(self, cat)


class _RankerByQueries_Sum(_Ranker):
  '''a sorter corresponding to 'RankByQueries_Sum'.'''
  def _group(self, seq):
    spec = self._spec; cat = self._cat
    mv = spec.getQueryValueSum(); vqs = spec._getValueQuerySequence()
    def generate(seq, vqs, mv):
      if not vqs: yield 0, seq; return
      vqs = vqs[:] # avoid side effects
      v,q = vqs.pop(); mv -= v
      q = And(LiteralResultSet(seq), q)
      qr = _eval(q, cat)
      if qr:
        feed1 = generate(qr, vqs, mv)
        seq = difference(seq, qr)
      else: feed1 = None
      feed2 = seq and generate(seq, vqs, mv) or None
      def fetch1():
        if feed1 is None: return None
        try: val, subseq = feed1.next(); return val + v, subseq
        except StopIteration: return None
      def fetch2():
        if feed2 is None: return None
        try: return feed2.next()
        except StopIteration: return None
      g1 = fetch1()
      # largest value from "feed1" only
      while g1 is not None and g1[0] > mv: yield g1; g1 = fetch1()
      # merge largest values from "feed1" and "feed2"
      g2 = fetch2()
      while g1 is not None and g2 is not None:
        v1 = g1[0]; v2 = g2[0]
        if v1 > v2: yield g1; g1 = fetch1()
        elif v2 > v1: yield g2; g2 = fetch2()
        # Note: g1[1] was copied (by the "intersection" above); therfore,
        #  we can destructively change it
        else: g1[1].update(g2[1]); yield g1; g1 = fetch1(); g2 = fetch2()
      # handle feed1
      while g1 is not None: yield g1; g1 = fetch1()
      # handle feed2
      while g2 is not None: yield g2; g2 = fetch2()
    for g in generate(seq, vqs, mv): yield g


class RankByQueries_Sum(_RankByQueries):
  '''Rank by the sum of query values for matching queries.

  The rank of a document *d* is the sum the query values for those
  queries that match *d*.
  '''
  _RankerClass = _RankerByQueries_Sum


class _RankerByQueries_Max(_Ranker):
  '''a sorter corresponding to 'RankByQueries_Max'.'''
  def _group(self, seq):
    spec = self._spec; cat = self._cat
    vqs = spec._getValueQuerySequence()
    for i in xrange(len(vqs)-1,-1,-1):
      v,q = vqs[i]
      q = And(LiteralResultSet(seq), q)
      qr = _eval(q, cat)
      if qr: yield v, qr; seq = difference(seq, qr)
      if not seq: return
    yield 0, seq


class RankByQueries_Max(_RankByQueries):
  '''Rank be the maximum of query values for mathing queries.

  The rank of a document *d* is the maximal query value for
  those queries that match *d*.
  '''
  _RankerClass = _RankerByQueries_Max

  def __init__(self, *specs):
    _RankByQueries.__init__(self, *specs)
    # merge successive queries with the same value
    nspecs = []; cv = None
    for v,q in self._specs:
      if v == cv:
        ls = nspecs[-1]
        nspecs[-1] = (ls[0], ls[1] | q)
      else: nspecs.append((v,q)); cv = v
    self._specs = nspecs

  def getQueryValueMax(self): return self._spec[-1][0]
  
