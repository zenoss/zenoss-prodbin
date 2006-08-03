# Copyright (C) 2004 by Dr. Dieter Maurer, Eichendorffstr. 23, D-66386 St. Ingbert, Germany
# see "LICENSE.txt" for details
#       $Id: RangeIndex.py,v 1.7 2006/04/09 16:52:03 dieter Exp $
'''An efficient index for ranges.'''

from BTrees.IIBTree import IISet, multiunion, IITreeSet

from ManagableIndex import ManagableIndex, addForm, setOperation
from Evaluation import Eval
from fixPluginIndexes import parseIndexRequest


class RangeIndex(ManagableIndex):
  '''A 'RangeIndex' has exactly 2 'ValueProviders': for the lower
  and upper bound, respectively.
  
  For a term *t*, it can efficiently return the documents *d*
  with: *lowerbound(d) <= t <= upperbound(d)*.
  '''

  meta_type = 'Managable RangeIndex'

  query_options= ('operator', 'isearch', 'isearch_filter')

  _properties = (
    ManagableIndex._properties
    + (
    {'id':'IgnoreIncompleteRange',
     'label':'Ignore incomplete ranges (otherwise, we raise a ValueError)',
     'type':'boolean', 'mode':'rw',},
    {'id':'BoundaryNames',
     'label':'Boundary names: "low" "high" pair specifying that this index should handle "low <= value <= high" queries"',
     'type':'tokens', 'mode':'rw',},
    {'id':'MinimalValue',
     'label':'Minimal value: values at or below this value are identified -- clear+reindex after change!',
     'type':'string', 'mode':'rw',},
    {'id':'MaximalValue',
     'label':'Maximal value: values at or above this value are identified -- clear+reindex after change!',
     'type':'string', 'mode':'rw',},
    {'id':'OrganisationHighThenLow',
     'label':"Organisation 'high-then-low': check when 'x <= high' is less likely than 'low <= x' -- clear+reindex after change",
     'type':'boolean', 'mode':'rw', },
    )
    )
  IgnoreIncompleteRange = 1
  BoundaryNames = ()
  MinimalValue = MaximalValue = ''
  OrganisationHighThenLow = False

  Combiners = ManagableIndex.Combiners + ('aggregate',)

  def __init__(self, name):
    self._minEvaluator = Eval('MinimalValue')
    self._maxEvaluator = Eval('MaximalValue')
    RangeIndex.inheritedAttribute('__init__')(self, name)

  _minValue = _maxValue = None # backward compatibility
  def _setup(self):
    RangeIndex.inheritedAttribute('_setup')(self)
    self._minValue = self._maxValue = None
    self._unrestriced = self._upperOnly = self._lowerOnly = None
    if hasattr(self, 'aq_base'): # wrapped
      eval = self._minEvaluator
      if eval._getExpressionString(): min = eval._evaluate(None, None)
      else: min = None
      if min is not None: min = self._standardizeTerm(min, None, 1, 0)
      self._minValue = min
      eval = self._maxEvaluator
      if eval._getExpressionString(): max = eval._evaluate(None, None)
      else: max = None
      if max is not None: max = self._standardizeTerm(max, None, 1, 0)
      self._maxValue = max
      it = self._index.__class__
      if min is not None and max is not None:
        if min > max:
          raise ValueError('Rangeindex %s: minimal exceeds maximal value: %s %s'
                           % (self.id, str(min), str(max))
                           )
        self._unrestricted = it()
      if min is not None: self._upperOnly = it()
      if max is not None: self._lowerOnly = it()

  def _standardizeValue(self, value, object):
    if not value: return
    value = [self._standardizeTerm(v, object, 1) for v in value]
    value = [v for v in value if v is not None]
    if not value: return
    if len(value) != 2:
      if self.IgnoreIncompleteRange: return
      raise ValueError('RangeIndex %s: wrong value %s for object %s'
                       % (self.id, str(value), object.absolute_url(1),),
                       )
    if value[0] > value[1]: return # empty range
    return value

  _combine_aggregate = _standardizeValue

  # do we need this?
  def uniqueValues(self, name=None, withLength=0): raise NotImplementedError

  # we do not support range searches
  def _enumerateRange(self, lo, hi): raise NotImplementedError

  # we do not support sorting
  def keyForDocument(self, docId): raise NotImplementedError
  def items(self): raise NotImplementedError

  # we do not support expanding
  def _getExpansionIndex(self): raise NotImplementedError


  # basic specialized methods
  def _indexValue(self,documentId,val,threshold):
    self._insert(val,documentId)
    return 1

  def _unindexValue(self,documentId,val):
    self._remove(val,documentId)


  # apply -- for (partial) plugin replacement for effective/expires
  def _apply_index(self,request, cid= ''):
    r = RangeIndex.inheritedAttribute('_apply_index')(self,request, cid)
    if r is not None or not self.BoundaryNames: return r
    bn = self.BoundaryNames
    if len(bn) != 2:
      raise ValueError('RangeIndex %s: "BoundaryNames" is not a pair'
                       % self.id
                       )
    ln, hn = bn
    lq = parseIndexRequest(request, ln, ManagableIndex.query_options)
    hq = parseIndexRequest(request, hn, ManagableIndex.query_options)
    if lq.keys != hq.keys \
       or lq.get('range') != 'min' \
       or hq.get('range') != 'max' \
       or lq.get('operator') \
       or hq.get('operator') \
       : return
    return RangeIndex.inheritedAttribute('_apply_index')(
      self,
      {self.id:{'query':lq.keys}},
      cid
      )
    

  # overridden _searchTerm to pass "isearch" into "_load"
  # ATT: the base class should do that but it would break compatibility
  def _searchTerm(self,term,record):
    return self._load(term, record.get('isearch'))

  
  # adapted storage
  def _findDocList(self, term, create):
    '''return for *term* a docList access path consisting
    of (index, key) pairs or 'None'.

    If *create*, create missing intermediates.
    '''
    lv, hv = term
    min = self._minValue; max = self._maxValue
    if min is not None and lv <= min:
      # no lower restriction
      if max is not None and hv >= max:
        # no upper restriction, i.e. unrestricted
        return ((self._unrestricted,min),)
      else: return ((self._upperOnly, hv),)
    elif max is not None and hv >= max:
      # no upper restriction
      return ((self._lowerOnly, lv),)
    elif self.OrganisationHighThenLow:
      idx = self._index; hi = idx.get(hv)
      if hi is None:
        if not create: return
        hi = idx[hv] = idx.__class__()
      return ((idx, hv), (hi, lv),)
    else:
      idx = self._index; li = idx.get(lv)
      if li is None:
        if not create: return
        li = idx[lv] = idx.__class__()
      return ((idx, lv), (li, hv),)

  def _insert(self, term, docId, _isInstance= isinstance, _IntType= int):
    '''index *docId* under *term*.'''
    i,k = self._findDocList(term, 1)[-1]
    dl = i.get(k)
    if dl is None: i[k] = docId; self.__len__.change(1); return
    if _isInstance(dl,_IntType): dl = i[k]= IITreeSet((dl,))
    dl.insert(docId)
    

  def _remove(self, term, docId, _isInstance= isinstance, _IntType= int):
    '''unindex *docId* under *term*.'''
    access = self._findDocList(term, 0)
    if access is not None: i,k = access[-1]; dl = i.get(k)
    else: dl = None
    isInt = _isInstance(dl,_IntType)
    if dl is None or isInt and dl != docId:
      raise ValueError('Attempt to remove nonexisting document %s from %s'
                       % (docId, self.id)
                       )
    if isInt: dl = None
    else: dl.remove(docId)
    if not dl:
      del i[k]; self.__len__.change(-1)
      if not i and len(access)==2: del access[0][0][access[0][1]]
    
  def _mkSet(self, dl,  _isInstance= isinstance, _IntType= int):
    if dl is None: return IISet()
    if _isInstance(dl, _IntType): dl = IISet((dl,))
    return dl

  def _load(self, term, isearch=False):
    '''return IISet for documents matching *term*.'''
    sets = []; mkSet = self._mkSet
    if self.OrganisationHighThenLow:
      for hi in self._index.values(term):
        for dl in hi.values(None, term): sets.append(mkSet(dl))
    else:
      for li in self._index.values(None, term):
        for dl in li.values(term): sets.append(mkSet(dl))
    min = self._minValue; max = self._maxValue
    if min is not None:
      for dl in self._upperOnly.values(term): sets.append(mkSet(dl))
    if max is not None:
      for dl in self._lowerOnly.values(None, term): sets.append(mkSet(dl))
      if min is not None: sets.append(mkSet(self._unrestricted.get(min)))
    return setOperation('or', sets, isearch)

  # filtering support
  supportFiltering = True

  def _makeTermPredicate(self, term):
    min = self._minValue; max = self._maxValue
    if min is not None and term < min: term = min
    if max is not None and term > max: term = max
    return lambda (low,high), t=term: low <= t <= high
  


def addRangeIndexForm(self):
  '''add RangeIndex form.'''
  return addForm.__of__(self)(
    type= RangeIndex.meta_type,
    description= '''A RangeIndex indexes an object under a range of terms.''',
    action= 'addIndex',
    )
