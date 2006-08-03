# Copyright (C) 2003-2006 by Dr. Dieter Maurer, Eichendorffstr. 23, D-66386 St. Ingbert, Germany
# see "LICENSE.txt" for details
#       $Id: AdvancedQuery.py,v 1.13 2006/07/14 19:07:28 dieter Exp $
'''Advanced Query

see 'AdvancedQuery.html' for documentation.
'''
from copy import copy

from ExtensionClass import Base

from types import InstanceType

from DateTime import DateTime
from BTrees.IIBTree import IISet, IITreeSet, \
     difference, union, multiunion, intersection
from BTrees.OOBTree import OOBTree

_notPassed= []


##############################################################################
## Query classes

class _BaseQuery(Base):
  ''''Query' base class.'''
  
  # Interface
  def __str__(self):
    raise NotImplementedError

  def _eval(self,catalog):
    raise NotImplementedError

  def __and__(self, other):
    '''self & other'''
    if isinstance(self,And): r = self._clone()
    else: r = And(self)
    r.addSubquery(other)
    return r

  def __or__(self, other):
    '''self | other'''
    if isinstance(self,Or): r = self._clone()
    else: r = Or(self)
    r.addSubquery(other)
    return r

  def __invert__(self):
    '''~ self'''
    return Not(self)

  def _clone(self):
    '''ATT: not a true clone operation.'''
    return self


class _ElementaryQuery(_BaseQuery):
  # to be overridden by derived classes
  _functor= None # transform term into query ("None" means identity)
  _OP= None     # used for display

  def __init__(self, idx, term, filter=False):
    self._idx = idx
    self._term = term
    self._filter = filter

  def __str__(self):
    return '%s %s %r' % (self._idx, self._OP, self._term)

  def _getTerm(self, term = _notPassed):
    '''determine term to be used for querying.
    '''
    if term is _notPassed: term = self._term
    return term


  def _eval(self,context):
    functor = self._functor
    term = self._getTerm()
    if functor is not None: term = functor(term)
    return context._applyIndex(self, term)


class Eq(_ElementaryQuery):
  '''idx = term'''
  _OP = '='
  def _functor(self,term): return (term,)

class Le(_ElementaryQuery):
  ''' idx <= term'''
  _OP = '<='
  def _functor(self,term): return {'query':term, 'range':'max'}

class Ge(_ElementaryQuery):
  ''' idx >= term'''
  _OP = '>='
  def _functor(self,term): return {'query':term, 'range':'min'}

class MatchGlob(_ElementaryQuery):
  '''idx = term'''
  _OP = '=~'
  def _functor(self,term): return {'query':term, 'match':'glob'}

class MatchRegexp(_ElementaryQuery):
  '''idx = term'''
  _OP = '=~~'
  def _functor(self,term): return {'query':term, 'match':'regexp'}

class Generic(_ElementaryQuery):
  _OP = '~~'

class In(Generic):
  _OP = 'in'

class Between(_ElementaryQuery):
  '''lb <= idx <= ub'''
  def __init__(self, idx, lb, ub, filter=False):
    _ElementaryQuery.__init__(self, idx, (lb,ub), filter)
   
  def __str__(self):
    t = self._term
    return '%r <= %s <= %r' % (t[0], self._idx, t[1])

  def _functor(self, term): return {'query':term, 'range':'min:max',}


class Indexed(_BaseQuery):
  def __init__(self, idx):
    self._idx = idx

  def __str__(self): return 'Indexed(%s)' % self._idx

  def _eval(self,context):
    return context._indexed(self._idx)


class Not(_BaseQuery):
  '''~(query)'''
  def __init__(self,query):
    self._query = query

  def __str__(self):
    return '~(%s)' % str(self._query)

  def _eval(self,context):
    return difference(context._getObjectIds(),self._query._eval(context))


class _CompositeQuery(_BaseQuery):
  # to be overridden
  _OP = None

  def __init__(self, *queries):
    self._subqueries= []
    for q in queries: self.addSubquery(q)

  def __str__(self):
    return '(%s)' % (' %s ' % self._OP).join([str(q) for q in self._subqueries])

  addSubquery__roles__ = None # Public
  def addSubquery(self,query):
    assert isinstance(query,_BaseQuery)
    self._subqueries.append(query)
    return self

  def _clone(self):
    return self.__class__(*self._subqueries)

  def _classifySubqueries(self):
    '''auxiliary method to classify subqueries into various categories:

    'empty' -- empty subquery; leading to a degenerated evaluation

    'index lookup' -- assumed to be fast and giving small results

    'complex' -- some complex subquery of different type (subqueries of
      the same type are included)

    'indexed' -- assumed to give rather large results

    'notQ' -- expensive, large results expected
    '''
    sqs = self._subqueries[:]
    empty = []; lookup = []; complex = []; indexed = []; notQ = []
    while sqs:
      q= sqs.pop()
      if isinstance(q,_ElementaryQuery): lookup.append(q); continue
      if q.__class__ is self.__class__:
        # swallow
        sqs.extend(q._subqueries)
        continue
      if isinstance(q,_CompositeQuery):
        if not q._subqueries: empty.append(q); break # degenerate
        complex.append(q)
        continue
      if isinstance(q,Not): notQ.append(q); continue
      indexed.append(q); continue
    if empty: return {'empty':1} # this is by purpose -- to get remembered when we should derive another class from "_CompositeQuery"
    return {'empty':empty, 'lookup':lookup, 'complex':complex,
            'indexed':indexed, 'notQ':notQ,
            }

      
class And(_CompositeQuery):
  _OP = '&'
  __iand__ = _CompositeQuery.addSubquery
  def _eval(self,context):
    csq = self._classifySubqueries()
    if csq['empty']: return IISet() # empty result
    nsq = csq['lookup'] + csq['complex'] + csq['indexed']
    notsq = csq['notQ']
    if not nsq and not notsq:
      # an empty 'And' query
      return context._getObjectIds()
    if not nsq: nsq.append(notsq.pop())
    r = None
    for q in nsq: r = intersection(r, q._eval(context))
    for q in notsq: r = difference(r, q._query._eval(context))
    return r


class Or(_CompositeQuery):
  _OP = '|'
  __ior__ = _CompositeQuery.addSubquery
  def _eval(self,context):
    csq = self._classifySubqueries()
    if csq['empty']: return context._getObjectIds()
    sqs= csq['lookup'] + csq['complex'] + csq['indexed'] + csq['notQ']
    if not sqs: return IISet()
    if len(sqs) >= 4: return multiunion([q._eval(context) for q in sqs])
    r = None
    for q in sqs: r = union(r,q._eval(context))
    return r


class LiteralResultSet(_BaseQuery):
  '''Query given by its result set.

  Used to restrict previous query results.
  '''
  def __init__(self, set):
    '''query returning *set*.

    *set* must be an 'IISet' or 'IITreeSet' of catalog record ids.
    '''
    if not isinstance(set, (IISet, IITreeSet)): set = IITreeSet(set)
    self._set = set

  def __str__(self): return 'LiteralResultSet(%s)' % self._set

  def _eval(self,catalog):
    return _wrapLookup(self._set)
  


#############################################################################
## Auxiliaries
# overridden when IncrementalSearch is present
def _wrapLookup(r):
  if not isinstance(r, (IISet, IITreeSet)): r = IITreeSet(r.keys())
  return r

# overridden when IncrementalSearch is present
def _prepareSpec(spec, query): return spec


class _QueryContext:
  '''auxiliary class to encapsulate the catalog interface.'''
  def __init__(self, catalog):
    self._catalog = catalog

  def _applyIndex(self, query, spec):
    spec = _prepareSpec(spec, query)
    cat = self._catalog; index = query._idx
    return _wrapLookup(cat.indexes[index].__of__(cat)._apply_index({index:spec})[0])

  # exists to be overridden by derived classes
  def _prepareSpec(self, spec, query): return spec

  _objects= None
  def _getObjectIds(self):
    objs = self._objects
    if objs is None:
      objs = self._objects = IITreeSet(self._catalog.data.keys())
    return objs

  def _indexed(self, index):
    cat = self._catalog
    # simplified -- hopefully not wrong!
    #return _wrapLookup(IITreeSet(cat.indexes[index]._unindex.keys()))
    return _wrapLookup(cat.indexes[index]._unindex)


#############################################################################
## Redefinitions when 'IncrementalSearch[2]' is available
ISearch = None
try: from IncrementalSearch2 import IAnd_int as IAnd, IOr_int as IOr, \
     INot, IBTree, Enumerator as EBTree, intersection_int as intersection, \
     ISearch
except ImportError: pass

if ISearch is None:
  try:
    from IncrementalSearch import IAnd, IOr, INot, ISearch, IBTree, EBTree, \
         intersection
    #raise ImportError # for testing purposes
  except ImportError: pass

if ISearch is None:
  class ISearch: pass
  IBTree = ISearch
else:
  class And(And):
    def _eval(self, context):
      subqueries = self._subqueries
      if not subqueries: return IBTree(context._getObjectIds()) # empty And
      if len(subqueries) == 1: return subqueries[0]._eval(context)
      search = IAnd(*[sq._eval(context) for sq in subqueries])
      search.complete()
      return search

  class Or(Or):
    def _eval(self, context):
      subqueries = self._subqueries
      if len(subqueries) == 1: return subqueries[0]._eval(context)
      search = IOr(*[sq._eval(context) for sq in subqueries])
      search.complete()
      return search

  class Not(Not):
    def _eval(self, context):
      return INot(self._query._eval(context), EBTree(context._getObjectIds()))

  def _prepareSpec(spec, query):
    filter = query._filter
    # add 'isearch' and 'isearch_filter' to *spec*
    # This is tricky -- we follow logic from
    # "Products.PluginIndexes.common.util.parseIndexRequest"
    if isinstance(spec, InstanceType) and not isinstance(spec, DateTime):
      spec = copy(spec)
      spec.isearch = True; spec.isearch_filter = filter
    elif isinstance(spec, dict):
      spec = spec.copy()
      spec['isearch'] = True; spec['isearch_filter'] = filter
    else: spec = {'query':spec, 'isearch':True, 'isearch_filter':filter}
    return spec

  def _wrapLookup(r):
    if r is None:
      # ATT: we could optimize this, but hopefully nobody specifies such
      # silly queries
      r = self._getObjectIds()
    if not isinstance(r, ISearch): r = IBTree(r)
    return r
