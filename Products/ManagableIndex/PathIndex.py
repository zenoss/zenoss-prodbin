# Copyright (C) 2004 by Dr. Dieter Maurer, Eichendorffstr. 23, D-66386 St. Ingbert, Germany
# see "LICENSE.txt" for details
#       $Id: PathIndex.py,v 1.3 2006/04/09 16:52:03 dieter Exp $
'''Path Index.'''

from BTrees.IOBTree import IOBTree
from BTrees.IIBTree import IISet

from ManagableIndex import ManagableIndex, addForm, setOperation, IFilter
from FieldIndex import FieldIndex

class PathIndex(ManagableIndex):
  '''a managable 'PathIndex'.'''
  meta_type= 'Managable PathIndex'

  _properties = ManagableIndex._properties[:4]

  query_options= ('operator', 'level', 'depth', 'isearch', 'isearch_filter')

  def _setup(self):
    PathIndex.inheritedAttribute('_setup')(self)
    # create auxiliary index
    self._lengthIndex = IOBTree()
    self._depth = 0

  # do we need this?
  def uniqueValues(self, name=None, withLength=0): raise NotImplementedError

  # we do not support range searches
  def _enumerateRange(self, lo, hi): raise NotImplementedError

  # we do not support sorting
  def keyForDocument(self, docId): raise NotImplementedError
  def items(self): raise NotImplementedError

  # we do not support expanding
  def _getExpansionIndex(self): raise NotImplementedError

  # term normalization -- we currently do not handle unicode appropriately
  def _normalize(self, value, object):
    '''convert into a tuple.'''
    value = PathIndex.inheritedAttribute('_normalize')(self, value, object)
    if value is None: return
    if hasattr(value, 'upper'): value = value.split('/')
    return tuple(value)

  # basic methods
  def _indexValue(self, docId, val, threshold):
    for t in enumerate(val): self._insert(t, docId)
    vn = len(val)
    self._insertAux(self._lengthIndex, vn, docId)
    if vn > self._depth: self._depth = vn
    return 1

  def _unindexValue(self, docId, val):
    for t in enumerate(val): self._remove(t, docId)
    self._removeAux(self._lengthIndex, len(val), docId)

  # modified storage -- we implement Zope's PathIndex scheme
  #  At first, it appeared to be superior than our standard scheme.
  #  However, the implementation proved this wrong: it is slightly
  #  inferior (with respect to number of loads, load size and load time).
  #  Nevertheless, we keep it as it will make the matching implementation
  #  easier (should someone wants it).
  # Our length reflects the number of different segs, not the number
  #  of total index entries
  def _insert(self, (pos, seg), docId):
    index = self._index
    si = index.get(seg)
    if si is None: index[seg] = si = IOBTree(); self.__len__.change(1)
    self._insertAux(si, pos, docId)

  def _remove(self, (pos, seg), docId):
    index = self._index
    si = index[seg]
    self._removeAux(si, pos, docId)
    if not si: del index[seg]; self.__len__.change(1)

  def _load(self, (pos, seg)):
    index = self._index
    si = index.get(seg)
    if si is None: return IISet()
    return self._loadAux(si, pos)


  # search implementation
  def _searchTerm(self, path, record):
    level = record.get('level', 0)
    depth = record.get('depth')
    isearch = record.get('isearch')
    if not path: return self._searchLength(level, depth, isearch)
    if level is not None and level >= 0:
      return self._searchAt(path, level, depth, isearch)
    try: limit = self._depth + 1
    except ValueError: limit = 0
    limit -= len(path)
    if level is not None: limit = min(limit, -level+1)
    return setOperation(
      'or',
      [self._searchAt(path, l, depth, isearch) for l in range(limit)],
      isearch,
      )

  def _searchAt(self, path, pos, depth, isearch):
    '''search for *path* at *pos* restricted by *depth*.'''
    load = self._load
    sets = [load((i+pos, seg)) for (i,seg) in enumerate(path)]
    if depth is not None:
      sets.append(self._searchDepth(depth, pos + len(path), isearch))
    return setOperation('and', sets, isearch)

  def _searchDepth(self, depth, len, isearch):
    li = self._lengthIndex; load = self._loadAux
    if depth >= 0: return load(li, len+depth)
    return setOperation('or',
                        [load(li, d) for d in range(len, len-depth+1)],
                        isearch,
                        )

  def _searchLength(self, level, depth, isearch):
    try: limit = self._depth + 1
    except: limit = 0
    if level is None: level = -limit
    if depth is None: depth = -limit
    lo = hi = 0
    if level >= 0: lo += level; hi += level
    else: hi += -level
    if depth >= 0: lo += depth; hi += depth
    else: hi += -depth
    li = self._lengthIndex; load = self._loadAux
    if lo == hi: return load(li, lo)
    return setOperation('or',
                        [load(li,l) for l in range(lo, min(hi+1,limit))],
                        isearch,
                        )

  # filtering support
  supportFiltering = True

  def _getFilteredISearch(self, query):
    terms = query.keys
    level = query.get('level', 0)
    depth = query.get('depth')
    try: limit = self._depth + 1
    except: limit = 0
    if level is None: level = -limit
    if depth is None: depth = -limit
    op = query.get('operator', self.useOperator)
    if depth >= 0:
      if level >= 0:
        def predFactory(t):
          tn = len(t)
          rn = level + depth + tn
          return lambda v: len(v) == rn and v[level:level+tn] == t
      else: # level < 0
        def predFactory(t):
          tn = len(t)
          rn = depth + tn
          def pred(v):
            vn = len(v)
            return vn >= rn and rn - vn <= -level and v[-rn:-rn+tn] == t
          return pred
    else: # depth < 0
      if level >= 0:
        def predFactory(t):
          tn = len(t)
          rn = level + tn; mn = rn - depth
          def pred(v):
            vn = len(v)
            return rn <= vn <= mn and v[level:level+tn] == t
          return pred
      else: # level < 0
        def predFactory(t):
          tn = len(t)
          def pred(v):
            vn = len(v)
            for l in range(max(0, vn-tn+depth), min(-level,vn-tn)+1):
              if v[l:l+tn] == t: return True
            return False
          return pred
    subsearches = []
    makeFilter = self._makeFilter; enumerator = self._getFilterEnumerator()
    for t in terms:
      t = self._standardizeTerm(t)
      subsearches.append(IFilter(makeFilter(predFactory(t)), enumerator))
    return self._combineSubsearches(subsearches, op)


    


def addPathIndexForm(self):
  '''add PathIndex form.'''
  return addForm.__of__(self)(
    type= PathIndex.meta_type,
    description= '''A PathIndex indexes an object under a path (a tuple or '/' separated string).
    It can be queried for objects the path of which contains a given path with
    various possibilities to contrain where the given path must
    lie within the objects path.''',
    action= 'addIndex',
    )
