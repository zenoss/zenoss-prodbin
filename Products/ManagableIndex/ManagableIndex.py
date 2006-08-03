# Copyright (C) 2003-2006 by Dr. Dieter Maurer, Eichendorffstr. 23, D-66386 St. Ingbert, Germany
# see "LICENSE.txt" for details
#       $Id: ManagableIndex.py,v 1.14 2006/05/05 18:06:48 dieter Exp $
'''Managable Index abstract base class.'''

import copy
from types import IntType, LongType, FloatType, \
     StringType, UnicodeType, \
     TupleType, InstanceType
from sys import modules, getdefaultencoding
from re import escape, compile

from Globals import InitializeClass
from Acquisition import aq_base
from AccessControl import ClassSecurityInfo
from BTrees.IOBTree import IOBTree
from BTrees.IIBTree import IISet, IITreeSet, union, intersection, multiunion
from BTrees.OOBTree import OOBTree, OOTreeSet
from BTrees.Length import Length
from DateTime.DateTime import DateTime

from Products.OFolder.OFolder import OFolder
from Products.PluginIndexes.common.PluggableIndex import PluggableIndexInterface
from Products.PluginIndexes.common.util import parseIndexRequest
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from fixPluginIndexes import parseIndexRequest
from Evaluation import Normalize, Ignore, EvalAndCall
from ValueProvider import AttributeLookup, ExpressionEvaluator
from Utils import reverseOrder, _LazyMap, \
     convertToDateTime, convertToDateTimeInteger, convertToDateInteger

_mdict= globals()

ManageManagableIndexes= "ManagableIndex: manage"


_TermTypeList= (
      'not checked',
      'string',
      'ustring',
      'integer',
      'numeric',
      'DateTime',
      'DateTimeInteger',
      'DateInteger',
      'tuple',
      'instance',
      'expression checked',
      )

_IntegerTypes = 'integer DateTimeInteger DateInteger'.split()

_TermCopyList= (
      'none',
      'shallow',
      'deep',
      )


class ManagableIndex(OFolder,Normalize, Ignore):
  '''Abstract base class for 'ManagableIndex'.'''

  security= ClassSecurityInfo()
  security.declareProtected(
    ManageManagableIndexes,
    'addAttributeLookupForm',
    'addExpressionEvaluatorForm',
    'addValueProvider',
    'manage_propertiesForm', 'manage_changeProperties', 'manage_editProperties',
    'indexSize',
    )
  security.declarePrivate(
    'getReverseOrder',
    )


  icon= 'misc_/PluginIndexes/index.gif'

  manage_options= (
    OFolder.manage_options[:1]
    + OFolder.manage_options[2:]
    )

  operators= ('or', 'and',)
  useOperator= 'or'
  query_options= ('operator', 'range', 'usage', 'match', 'isearch', 'isearch_filter')
  Combiners= ('useFirst',)

  NormalizerProperty= 'NormalizeTerm'
  IgnoreProperty= 'StopTermPredicate'

  _properties= (
    (
      { 'id' : 'CombineType', 'type' : 'selection', 'mode' : 'w', 'select_variable' : 'listCombiners',
        'label':'Combine type: determines how values from value providers are combined'},
      {'id':'PrenormalizeTerm', 'type':'string', 'mode':'w',
       'label':'Term prenormalizer: applied to terms before term expansion in queries and (always) before stop term elimination; used e.g. for case normalization, stemming, phonetic normalization, ...',},
      {'id' : IgnoreProperty, 'type' : 'string', 'mode' : 'w',
       'label':'Stop term predicate: used to recognized and eliminate stop terms; used always (except in range queries) after prenormalization',},
      {'id' : NormalizerProperty, 'type' : 'string', 'mode' : 'w',
       'label':'Term normalizer: applied to terms before type checking; used e.g. for encoding the term into a efficient form',},
      { 'id' : 'TermType', 'type' : 'selection', 'mode' : 'w', 'select_variable' : 'listTermTypes',
        'label':'Term type: used to convert and check the terms type; may allows to choose specially optimized index structures (e.g. for integer types) or provide additional features (e.g. term expansions for string types) -- clear+reindex after change!',
        },
      { 'id' : 'TermTypeExtra', 'type' : 'string', 'mode' : 'w',
        'label':'Term type argument: required by some term types (see the documentation)',},
      { 'id' : 'TermCopy', 'type' : 'selection', 'mode' : 'w', 'select_variable' : 'listCopyTypes',
        'label':'Control term copying: may be necessary for mutable terms to prevent index corruption',},
      )
    )
  TermType= _TermTypeList[0]
  TermTypeExtra= ''
  TermCopy= _TermCopyList[0]
  CombineType= Combiners[0]
  NormalizeTerm= ''
  PrenormalizeTerm= ''
  StopTermPredicate= ''

  __implements__= PluggableIndexInterface

  def __init__(self,name):
    self.id= name
    self.clear()
    self._createDefaultValueProvider()

  def clear(self):
    '''clear the index.'''
    l = self.__len__
    if isinstance(l, Length): l.set(0)
    else: self.__len__ = Length()
    try: self.numObjects.set(0)
    except AttributeError: self.numObjects= Length()
    if self.ReverseOrder: self._reverseOrder = OOTreeSet()
    self._setup()

  def __len__(self):
    '''Python 2.4 requires this to be defined inside the class.'''
    l = self.__len__
    if not isinstance(l, Length): l = self.__len__ = Length()
    return l()

  def indexSize(self):
    return self.__len__()

  def _setup(self):
    self._unindex= IOBTree()
    treeType = self.TermType in _IntegerTypes and IOBTree or OOBTree
    self._index= treeType()

  def _createDefaultValueProvider(self):
    self.addValueProvider(self.id,'AttributeLookup')

  ## term expansion -- provided for indexes with declared "string" and "ustring"
  ## term types
  def matchGlob(self, t):
    '''match '*' (match any sequence) and '?' (match any character) in *t* returning a list of terms.'''
    # leads to wrong result -- would need to check against index
    # if not ('*' in t or '?' in t): return [t]
    regexp = glob2regexp(t)
    return self.matchRegexp(regexp+'$')

  _matchType = None
  def matchRegexp(self, regexp):
    '''match *regexp* into a list of matching terms.

    Note that for efficiency reasons, the regular expression
    should have an easily recognizable plain text prefix -- at
    least for large indexes.
    '''
    prefix, regexp = _splitPrefixRegexp(regexp)
    termType = self._matchType or self.TermType
    if termType == 'string': prefix = str(prefix); regexp = str(regexp)
    elif termType == 'ustring': prefix = unicode(prefix); regexp = unicode(regexp)
    elif termType == 'asis': pass
    else: raise ValueError(
      "Index %s has 'TermType/MatchType' %s not supporting glob/regexp expansion"
      % (self.id, termType)
      )
    index = self._getMatchIndex(); pn = len(prefix)
    l = []; match = compile(regexp).match
    for t in index.keys(prefix): # terms starting prefix
      if not t.startswith(prefix): break
      if match(t[pn:]): l.append(t)
    return l

  def _getMatchIndex(self):
    '''the index used for expansion'''
    return self._index

  ## match filtering
  def matchFilterGlob(self, t):
    '''see 'matchGlob' but for filtering.'''
    regexp = glob2regexp(t)
    return self.matchFilterRegexp(regexp+'$')

  def matchFilterRegexp(self, regexp):
    '''see 'matchRegexp' but for filtering.'''
    termType = self._matchType or self.TermType
    if termType == 'string': regexp = str(regexp)
    elif termType == 'ustring': regexp = unicode(regexp)
    elif termType == 'asis': pass
    else: raise ValueError(
      "Index %s has 'TermType/MatchType' %s not supporting glob/regexp expansion"
      % (self.id, termType)
      )
    return compile(regexp).match


  ## Responsibilities from 'PluggableIndexInterface'
  # 'getId' -- inherited from 'SimpleItem'

  def getEntryForObject(self,documentId, default= None):
    '''Information for *documentId*.'''
    info= self._unindex.get(documentId)
    if info is None: return default
    return repr(info)


  def index_object(self,documentId,obj,threshold=None):
    '''index *obj* as *documentId*.

    Commit subtransaction when *threshold* index terms have been indexed.
    Return the number of index terms indexed.
    '''
    # Note: objPath should be provided by the catalog -- but it is not
    try: objPath = obj.getPhysicalPath()
    except: objPath = None
    __traceback_info__ = self.id, objPath

    val= self._evaluate(obj)

    # see whether something changed - do nothing, if it did not
    oldval= self._unindex.get(documentId)
    if val == oldval: return 0
    # some data types, e.g. "OOSet"s do not define a senseful "==".
    #  provide a hook to handle this case
    customEqual= self._equalValues
    if customEqual is not None and customEqual(val,oldval): return 0

    # remove state info
    update= self._update
    if update is None or oldval is None or val is None:
      # no optimization
      if oldval is not None: self._unindex_object(documentId,oldval,val is None)
      if val is None: return 0
      rv= self._indexValue(documentId,val,threshold)
      if oldval is None: self.numObjects.change(1)
    else:
      # optimization
      rv= update(documentId,val,oldval,threshold)
      if isinstance(rv, tuple): return rv[0]

    # remember indexed value
    self._unindex[documentId]= val
    return rv


  def unindex_object(self,documentId):
    '''unindex *documentId*.

    ATT: why do we not have a *threshold*????
    '''
    # Note: objPath/documentId should be provided by the catalog -- but it is not
    __traceback_info__ = self.id, documentId

    val= self._unindex.get(documentId)
    if val is None: return # not indexed
    self._unindex_object(documentId,val,1)

  def _unindex_object(self,documentId,val,remove):
    self._unindexValue(documentId,val)
    if remove:
      del self._unindex[documentId]
      self.numObjects.change(-1)


  def uniqueValues(self, name=None, withLengths=0):
    '''unique values for *name* (???).

    If *withLength*, returns sequence of tuples *(value,length)*.
    '''
    if name is None: name= self.id
    if name != self.id: return ()
    values= self._index.keys()
    if not withLengths: return tuple(values)
    return tuple([(value,self._len(value)) for value in values])


  def _apply_index(self,request, cid= ''):
    '''see 'PluggableIndex'.

    What is *cid* for???
    '''
    __traceback_info__ = self.id

    record= parseIndexRequest(request, self.id, self.query_options)
    terms= record.keys
    if terms is None: return

    __traceback_info__ = self.id, record.keys

    op= record.get('operator', self.useOperator)
    if op not in self.operators:
      raise ValueError("operator not permitted: %s" % op)
    combine= op == 'or' and union or intersection

    filteredSearch = None
    if record.get('isearch') and record.get('isearch_filter') \
       and self.supportFiltering and IFilter is not None:
      filteredSearch = self._getFilteredISearch(record)

    if filteredSearch is None:
      match = record.get('match')
      if match is not None:
        l = []; match = getattr(self, 'match' + match.capitalize())
        prenorm = self._prenormalizeTerm
        for t in terms:
          t = prenorm(t, None)
          if t is not None: l.extend(match(t))
        terms = l

      range= record.get('range')
      if range is not None:
        terms= [self._standardizeTerm(t,elimStopTerm=0, prenormalize=not match) for t in terms]
        range= range.split(':'); lo= hi= None
        if 'min' in range: lo= min(terms)
        if 'max' in range: hi= max(terms)
        terms= self._enumerateRange(lo,hi)
      else:
        terms= [self._standardizeTerm(t, prenormalize=not match) for t in terms]

    if filteredSearch is None: r = self._search(terms,combine,record)
    else: r = filteredSearch
    if r is None: return
    return r, self.id


  #################################################################
  # search
  def _search(self,terms,combine,record):
    return setOperation(
      combine is union and 'or' or 'and',
      [self._searchTerm(t,record) for t in terms],
      record.get('isearch'),
      )

  def _searchTerm(self,term,record):
    return self._load(term)

  def _enumerateRange(self,min,max):
    '''enumerate terms between *min* and *max*.'''
    return self._index.keys(min,max)


  #################################################################
  # filtering
  supportFiltering = False

  def _getFilteredISearch(self, query):
    '''return a filtered search for *query*, if this seems promissing, or 'None'.
    '''
    preds = []
    enumerator = self._getFilterEnumerator(); makeFilter = self._makeFilter

    terms = query.keys
    match = query.get('match'); range = query.get('range')
    op = query.get('operator', self.useOperator)

    if match is not None:
      # we do not want to filter combined 'match' and 'range' queries
      if range is not None: return
      # can only filter 'or' matches
      if op != 'or': return
      # we can filter 'match' queries only if there is no 'normalizer'
      #  maybe, we should not filter, if there is an 'ignorer'?
      if self._hasNormalizer(): return
      l = []; match = getattr(self, 'matchFilter' + match.capitalize())
      prenorm = self._prenormalizeTerm
      for t in terms:
        t = prenorm(t, None)
        if t is not None: preds.append(match(t))
    else:
      range= query.get('range')
      if range is not None:
        # can only filter 'or' ranges
        if op != 'or': return
        terms= [self._standardizeTerm(t,elimStopTerm=0, prenormalize=not match) for t in terms]
        range= range.split(':'); lo= hi= None
        if 'min' in range: lo= min(terms)
        if 'max' in range: hi= max(terms)
        preds.append(_rangeChecker(lo,hi))
      else:
        makePred = self._makeTermPredicate; standardize = self._standardizeTerm
        preds = [
          makePred(standardize(t, prenormalize=not match))
          for t in terms
          ]
    subsearches = [IFilter(makeFilter(pred), enumerator) for pred in preds]

    return self._combineSubsearches(subsearches, op)

  def _combineSubsearches(self, subsearches, op):
    if len(subsearches) == 1: return subsearches[0]
    combine = op == 'or' and IOr or IAnd
    search = combine(*subsearches); search.complete()
    return search

  def _getFilterEnumerator(self):
    return Enumerator(self._unindex)

  def _makeTermPredicate(self, term):
    '''this is adequate for field and keyword indexes.'''
    return lambda x, t=term: x == t

  def _makeFilter(self, pred):
    '''a document filter 'did -> True/False' checking term predicate *pred*.

    This definition is adequate, when the predicate can be directly
    applied to the 'unindex' value.
    '''
    def check(did):
      dv = self._unindex.get(did)
      return dv is not None and pred(dv)
    return check


  #################################################################
  # required for sorting
  # no longer needed for Zope 2.7 -- keep for compatibility
  def keyForDocument(self, docId): return self._unindex[docId]
  def items(self):
    return [(k,self._load(k)) for k in self._index.keys()]


  #################################################################
  # Reverse ordering support
  def getReverseOrder(self):
    '''return the keys in reverse order.'''
    if self.ReverseOrder:
      return _LazyMap(lambda x: x.getValue(), self._reverseOrder.keys())


  #################################################################
  # Storage API
  # we implement a small optimization
  # a single document is stored as integer; more are stored as an IITreeSet
  ReverseOrder = 0

  def _insert(self,term,docId, _isInstance= isinstance, _IntType= IntType):
    '''index *docId* under *term*.'''
    index= self._index
    dl= index.get(term)
    if dl is None:
      index[term]= docId; self.__len__.change(1)
      if self.ReverseOrder: self._reverseOrder.insert(reverseOrder(term))
      return
    if _isInstance(dl,_IntType): dl= index[term]= IITreeSet((dl,))
    dl.insert(docId)

  def _remove(self,term,docId, _isInstance= isinstance, _IntType= IntType):
    '''unindex *docId* under *term*.'''
    index= self._index
    dl= index.get(term); isInt= _isInstance(dl,_IntType)
    if dl is None or isInt and dl != docId:
      raise ValueError('Attempt to remove nonexisting document %s from %s'
                       % (docId, self.id)
                       )
    if isInt: dl = None
    else: dl.remove(docId)
    if not dl:
      del index[term]; self.__len__.change(-1)
      if self.ReverseOrder: self._reverseOrder.remove(reverseOrder(term))

  def _load(self,term, _isInstance= isinstance, _IntType= IntType):
    '''the docId list for *term*.'''
    index= self._index
    dl= index.get(term)
    if dl is None: return IISet()
    if _isInstance(dl,_IntType): return IISet((dl,))
    return dl

  def _len(self,term):
    '''the number of documents indexed under *term*.'''
    return len(self._load(term))


  ###########################################################################
  ## methods to maintain auxiliary indexes
  ## we implement the same optimization as for the main index
  def _insertAux(self, index, term, docId):
    '''index *docId* under *term*.'''
    dl= index.get(term)
    if dl is None: index[term]= docId; return
    if isinstance(dl,int): dl= index[term]= IITreeSet((dl,))
    dl.insert(docId)

  def _removeAux(self, index, term, docId):
    '''unindex *docId* under *term*.'''
    dl= index.get(term); isInt= isinstance(dl,int)
    if dl is None or isInt and dl != docId:
      raise ValueError('Attempt to remove nonexisting document %s from %s'
                       % (docId, self.id)
                       )
    if isInt: dl = None
    else: dl.remove(docId)
    if not dl: del index[term]

  def _loadAux(self,index, term):
    '''the docId list for *term*.'''
    dl= index.get(term)
    if dl is None: return IISet()
    if isinstance(dl,int): return IISet((dl,))
    return dl
    


  #################################################################
  # Term standardization and checking
  def listTermTypes(self):
    '''the sequence of supported term types.'''
    return _TermTypeList

  def listCopyTypes(self):
    '''the sequence of term copy types.'''
    return _TermCopyList

  def listCombiners(self):
    '''the sequence of combine types.'''
    return self.Combiners

  def _standardizeTerm(self, value, object=None, copy=False, elimStopTerm=True, prenormalize=True):
    if prenormalize:
      value = self._prenormalizeTerm(value, object)
      if value is None: return
    if elimStopTerm:
      value= self._ignore(value,object)
      if value is None: return
    value= self._normalize(value,object)
    if value is None: return
    tt= self.TermType
    checker= _TermTypeMap[tt]
    if checker: value= checker(self,value,object)
    if copy and tt in ('not checked', 'instance', 'expression checked',):
      copy= _CopyTypeMap[self.TermCopy]
      if copy: value= copy(value)
    return value

  _prenormalizer = None
  def _prenormalizeTerm(self, value, object):
    PT = self.PrenormalizeTerm
    if not PT: return value
    normalizer = self._prenormalizer
    if normalizer is None:
      normalizer = self._prenormalizer = Normalize()
      normalizer.NormalizerProperty = 'PrenormalizeTerm'
    return normalizer._normalize(value, object)
    


  #################################################################
  # Evaluation
  def _evaluate(self,object):
    '''evaluate *object* with respect to this index.'''
    l= []; v= None
    combiner= self.CombineType; useFirst= combiner == 'useFirst'
    for vp in self.objectValues():
      v= vp.evaluate(object)
      if v is not None:
        if useFirst: break
        l.append(v)
    if useFirst:
      if v is None: return
      return self._standardizeValue(v,object)
    return getattr(self,'_combine_' + combiner)(l,object)

  def _standardizeValue(self,value,object):
    return self._standardizeTerm(value,object,1)
    


  #################################################################
  # to be defined by concrete deriving classes
  # _indexValue(self,documentId,val,threshold)
  # _unindexValue(self,documentId,val)


  #################################################################
  # optionally defined by concrete deriving classes
  # _update(self,documentId,val,oldval,threshold)
  #   returns number of entries added; if tuple, _unindex already updated
  # _equalValues(self,val1,val2) -- true, if standardized values are equal
  _update= None
  _equalValues= None


  #################################################################
  # Value provider management
  def all_meta_types(self):
    return (
      { 'name' : AttributeLookup.meta_type,
        'action' : 'addAttributeLookupForm',
        'permission' : ManageManagableIndexes,
        },
      { 'name' : ExpressionEvaluator.meta_type,
        'action' : 'addExpressionEvaluatorForm',
        'permission' : ManageManagableIndexes,
        },
      )

  def addAttributeLookupForm(self):
    '''addForm for 'AttributeLookup' value provider.'''
    return addForm.__of__(self)(
      type= 'AttributeLookup',
      description= '''An AttributeLookup is a value provider which evaluates an object by looking up an attribute of the object.''',
      action= 'addValueProvider',
      )

  def addExpressionEvaluatorForm(self):
    '''addForm for 'ExpressionEvaluator' value provider.'''
    return addForm.__of__(self)(
      type= 'ExpressionEvaluator',
      description= '''An ExpressionEvaluator is a value provider which evaluates an expression.''',
      action= 'addValueProvider',
      )

  def addValueProvider(self,id,type, RESPONSE=None):
    '''add a value provider with *id* of *type*.'''
    cl= _mdict[type] # ATT: maybe, we should check allowed types?
    # try to avaid a name conflict
    eid= id
    if not id.endswith('_') and hasattr(aq_base(self),id): eid= id + '_'
    vp= cl(); vp.id= eid
    if id != eid and type == 'AttributeLookup': vp.Name= id
    self._setObject(eid, vp)
    vp= self._getOb(eid)
    if RESPONSE is None: return vp
    RESPONSE.redirect('%s/manage_workspace' % vp.absolute_url())

    
InitializeClass(ManagableIndex)


#################################################################
# Term checking and copying

_CopyTypeMap= {
  'none' : None,
  'shallow' : copy.copy,
  'deep' : copy.deepcopy,
  }

def _isNumeric(value, _NumericType= (IntType, FloatType, LongType,)):
  try: return isinstance(value,_NumericType)
  except TypeError: # pre 2.3
    for t in _NumericType:
      if isinstance(value,t): return 1
  return 0

def _isString(value, _StringType= (StringType, UnicodeType,)):
  try: return isinstance(value,_StringType)
  except TypeError: # pre 2.3
    for t in _StringType:
      if isinstance(value,t): return 1
  return 0


def _checkNumeric(index,value,object):
  '''return *value*, maybe converted, if it is numeric.'''
  # see whether is has already the correct type
  if _isNumeric(value): return value
  try:
    if _isString(value):
      if '.' in value or 'E' in value or 'e' in value: value= float(value)
      else:
        try: value= int(value)
        except ValueError: value= long(value)
  except:
    raise TypeError("cannot convert %s to numeric" % str(value))
  return value


def _checkInteger(index,value,object):
  '''return *value*, maybe converted, if it is integer.'''
  if hasattr(index.aq_base, 'convertToInteger'):
    return index.convertToInteger(value, object)
  return int(value)


def _checkString(index,value,object):
  '''return *value*, maybe converted, if it is a string.'''
  if isinstance(value,StringType): return value
  try:
    nv= str(value)
  except: nv= None
  if value is None or nv.startswith('<'):
    raise TypeError("cannot convert %s to string" % str(value))
  return nv


def _checkUnicode(index,value,object, encode=None):
  '''return *value*, maybe converted, if it is a unicode string.'''
  if isinstance(value,UnicodeType): return value
  try:
    nv= unicode(value, encode or getdefaultencoding())
  except:
    raise TypeError("cannot convert %s to string" % str(value))
  return nv

def _checkUnicode_encode(index, value, object):
  # use 'TermTypeExtra' as encoding
  return _checkUnicode(index, value, object, index.TermTypeExtra)

def _checkUnicode_encode2(index, value, object):
  # use the value after ';' in 'TermTypeExtra' as encoding
  encoding = index.TermTypeExtra
  encoding = ';' in encoding and encoding.split(';',1)[1]
  return _checkUnicode(index, value, object, encoding)


def _checkDateTime(index,value,object):
  '''return *value* (in sec since epoch), if it is a 'DateTime' instance.'''
  if isinstance(value, float): return value
  return convertToDateTime(value)._t # float

def _checkDateTimeInteger(index, value, object):
  return convertToDateTimeInteger(value)

def _checkDateInteger(index, value, object):
  return convertToDateInteger(value)

def _checkInstance(index,value,object):
  '''return *value*, if it is an instance of class 'index.TermTypeExtra'.'''
  fullClassName= index.TermTypeExtra
  cl= _findClass(fullClassName)
  if isinstance(value,cl):
    if hasattr(cl,'__cmp__'): return value
    raise TypeError("class %s does not define '__cmp__'" % fullClassName)
  raise TypeError("cannot convert %s to %s" % (str(value),fullClassName))


def _findClass(cl):
  '''return the class identified by full class name *cl*.'''
  cs= cl.split('.')
  mod,cn= '.'.join(cs[:-1]), cs[-1]
  return getattr(modules[mod],cn)

def _checkTuple(index,value,object):
  '''return *value*, if it matches the tuple spec in 'index.TermTypeExtra'.'''
  spec= index.TermTypeExtra.split(';',1)[0]
  value,pos= _checkTuple_(index,value,spec,0)
  if pos != len(spec):
    raise TypeError("%s does not conform to %s" % (str(value),spec))
  return value


def _checkTuple_(index,value,spec,pos):
  '''return *value*, if it conforms to *spec*.'''
  if _isString(value):
    raise TypeError("%s does not conform to %s" % (str(value),spec))
  try:
    value= tuple(value)
  except TypeError:
      raise TypeError("%s does not conform to %s" % (str(value),spec))
  i= 0; n= len(value)
  while i < n:
    v= value[i]
    if pos >= len(spec):
      raise TypeError("%s does not conform to %s" % (str(value),spec))
    si= spec[pos]; pos+= 1
    if si == '(':
      nv,pos= _checkTuple_(index,v,spec,pos)
      if spec[pos] != ')':
        raise TypeError("%s does not conform to %s" % (str(value),spec))
      pos+= 1
    else:
      checker= _TupleCheck[si]
      nv= checker(index,v,None)
    if v != nv:
      if isinstance(value,TupleType): value= list(value)
      value[i]= nv
    i+= 1
  return value, pos

def _checkWithExpression(index,value,object):
  '''return 'index.TermTypeExtra' applied to *value*, if not None.'''
  evaluator= getattr(index,'_v_checkEvaluator',None)
  if evaluator is None:
    evaluator= index._v_checkEvaluator= EvalAndCall('TermTypeExtra')
    evaluator= evaluator.__of__(index)
  nv= evaluator._evaluate(value,object)
  if nv is None:
    raise TypeError('%s is not accepted by %s' % (str(value),index.TermTypeExtra))
  return nv
    

_TermTypeMap= {
  'not checked' : None,
  'numeric' : _checkNumeric,
  'string' : _checkString,
  'integer' : _checkInteger,
  'ustring' : _checkUnicode_encode,
  'DateTime' : _checkDateTime,
  'DateTimeInteger' : _checkDateTimeInteger,
  'DateInteger' : _checkDateInteger,
  'tuple' : _checkTuple,
  'instance' : _checkInstance,
  'expression checked' : _checkWithExpression,
  }

_TupleCheck= {
  'n' : _checkNumeric,
  's' : _checkString,
  'u' : _checkUnicode_encode2,
  'd' : _checkDateTime,
  }


#################################################################
# constructor support
addForm= PageTemplateFile('zpt/addForm',_mdict)

def addIndex(self,id,type, REQUEST= None, RESPONSE= None, URL3= None):
  '''add index of *type* with *id*.'''
  return self.manage_addIndex(id, type, extra=None,
             REQUEST=REQUEST, RESPONSE=RESPONSE, URL1=URL3)



#################################################################
# auxiliaries
_escs = dict('a\a f\f n\n r\r t\t v\v'.split(' '))
_escs.update(dict([(c,0) for c in 'AbBdDsSwWZ']))

def _splitPrefixRegexp(regexp,
                       special_=dict(map(None, '.^$*+?{}|[]()', ())),
                       leftOps_=dict(map(None, '*+?{|', ())),
                       escs_=_escs.get,
                       ):
  '''return pair of plain text prefix and remaining regexp.'''
  if not regexp or regexp[0] in special_: return '', regexp
  prefix = ''; i = 0; n = len(regexp)
  while i < n:
    c = regexp[i]
    if c in special_:
      if c in leftOps_: return prefix[:-1], escape(prefix[-1]) + regexp[i:]
      return prefix, regexp[i:]
    elif c == '\\':
      c = regexp[i+1]
      # could be optimized but who cares
      if c.isdigit() or c == 'x': return prefix, regexp[i:]
      ec = escs_(c, c)
      if ec == 0: return prefix, regexp[i:]
      prefix += ec # ATT: quadratic -- but we do not expect it to become huge
      i += 1
    else: prefix += c # ATT: quadratic -- see above
    i += 1
  return prefix, ''

def glob2regexp(glob):
    return escape(glob).replace(r'\*','.*', ).replace(r'\?','.')

def _rangeChecker(lo, hi):
  if lo is None and hi is None: return lambda x: True
  if lo is None: return lambda x: x <= hi
  if hi is None: return lambda x: lo <= x
  return lambda x: lo <= x <= hi



#################################################################
# monkey patches

# give ZCatalogIndexes an id such that urls are correct
from Products.ZCatalog.ZCatalogIndexes import ZCatalogIndexes
ZCatalogIndexes.id= "Indexes"



#################################################################
# setOperation -- using 'IncrementalSearch', if available
def setOperation(op, sets, isearch):
  '''perform *op* on *sets*. if *isearch*, return an incremental search.

  *op* may be '"and"' or '"or"'.

  Uses 'IncrementalSearch', if available.
  '''
  if not sets:
    if op == 'and': return # None means all results
    if isearch: search = IOr(); search.complete(); return search
    return IISet()
  # Note: "multiunion" is *much* faster than "IOr"!
  #if IAnd is not None and (isearch or len(sets) > 1):
  if IAnd is not None and (isearch or (op == 'and' and len(sets) > 1)):
    isets = []
    for set in sets:
      if set is None:
        # all results
        if op == 'and': continue
        else: return
      if not isinstance(set, ISearch): set = IBTree(set)
      isets.append(set)
    if op == 'and' and not isets: return # empty 'and'
    cl = op == 'and' and IAnd or IOr
    if len(isets) == 1:
      # do not wrap a one element search
      search = isets[0]
    else: search = cl(*isets); search.complete()
    if isearch: return search
    if hasattr(search, 'asSet'): r = search.asSet()
    else: r = IISet(); r.__setstate__((tuple(search),))
    return r
  if op == 'or' and len(sets) > 5:
    r = multiunion(sets)
  else:
    combine = op == 'and' and intersection or union
    r= None
    for set in sets: r= combine(r,set)
    if r is None:
      if combine is union: r = IISet()
      else: return
    if isearch: r = IBTree(r)
  return r
  


IAnd = IOr = IBTree = IFilter = None

# try IncrementalSearch2 (the C implementation of IncrementalSearch)
try:
  from IncrementalSearch2 import \
       IAnd_int as IAnd, IOr_int as IOr, IBTree, ISearch
  try: from IncrementalSearch2 import IFilter_int as IFilter, \
       Enumerator
  except ImportError: pass
except ImportError: IAnd = None

# try IncrementalSearch
if IAnd is None:
  try:
    from IncrementalSearch import IAnd, IOr, IBTree, ISearch, \
         EBTree as Enumerator
    try:
      from IncrementalSearch import IFilter
    except ImportError: pass
  except ImportError: pass

