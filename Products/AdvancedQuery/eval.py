# Copyright (C) 2003-2006 by Dr. Dieter Maurer, Eichendorffstr. 23, D-66386 St. Ingbert, Germany
#       $Id: eval.py,v 1.2 2006/06/25 19:11:24 dieter Exp $
'''Query evaluation.

Put into its own module to avoid cyclic module imports.
'''
from BTrees.IIBTree import IISet

from Products.ZCatalog.Lazy import LazyCat, LazyMap

from AdvancedQuery import _QueryContext, ISearch, IBTree, _notPassed
from sorting import sort as _sort, normSortSpecs as _normSortSpecs

def _eval(query, cat):
  '''evaluate *query* in the context of *cat* (a 'Products.ZCatalog.Catalog.Catalog').'''
  rs = query._eval(_QueryContext(cat))
  if isinstance(rs, ISearch):
    if hasattr(rs, 'asSet'): rs = rs.asSet()
    elif isinstance(rs, IBTree): rs = rs.getTree()
    else: hits = tuple(rs); rs = IISet(); rs.__setstate__((hits,))
  return rs

def eval(catalog, query, sortSpecs=(), withSortValues=_notPassed):
  '''evaluate *query* for *catalog*; sort according to *sortSpecs*.

  *sortSpecs* is a sequence of sort specifications.
  
  A sort spec is either a ranking spec, an index name or a pair
  index name + sort direction ('asc/desc').

  If *withSortValues* is not passed, it is set to 'True' when *sortSpecs*
  contains a ranking spec; otherwise, it is set to 'False'.

  If *withSortValues*, the catalog brains 'data_record_score_' is
  abused to communicate the sort value (a tuple with one
  component per sort spec). 'data_record_normalized_score_' is
  set to 'None' in this case.
  '''
  cat = catalog._catalog
  rs = _eval(query, cat)
  if not rs: return LazyCat(())
  sortSpecs, withSortValues = _normSortSpecs(sortSpecs, withSortValues, cat)
  if sortSpecs or withSortValues: rs = _sort(rs, sortSpecs, withSortValues)
  if hasattr(rs, 'keys'): rs= rs.keys() # a TreeSet does not have '__getitem__'
  return LazyMap(cat.__getitem__, rs)
