# Copyright (C) 2003 by Dr. Dieter Maurer, Eichendorffstr. 23, D-66386 St. Ingbert, Germany
# see "LICENSE.txt" for details
#       $Id: test_ManagableIndex.py,v 1.10 2006/05/17 19:53:07 dieter Exp $

from TestBase import TestBase, genSuite, runSuite

from re import escape

from BTrees.OOBTree import OOSet
from BTrees.IIBTree import IISet
from BTrees.IOBTree import IOBTree
from DateTime.DateTime import DateTime

from Products.ManagableIndex.ValueProvider import ExpressionEvaluator
from Products.ManagableIndex.ManagableIndex import _splitPrefixRegexp
from Products.ManagableIndex.ManagableIndex import IFilter
from Products.ManagableIndex.KeywordIndex import KeywordIndex_scalable


class TestManagableIndex(TestBase):
  def test_AttributeLookup(self):
    fi= self.fi; ki= self.ki # field and keyword index
    obj1= self.obj1; obj2= self.obj2
    kw= OOSet((1,2,))
    ## Acquisition type
    # implicit
    self.assertEqual(fi._evaluate(obj2),'id')
    self.assertEqual(fi._evaluate(obj1),None)
    # "OOSet" does not support intelligent equality test
    self.assertEqual(ki._evaluate(obj2).keys(),kw.keys())
    self.assertEqual(ki._evaluate(obj1).keys(),kw.keys())
    # none
    ki.kw.AcquisitionType= 'none'
    self.assertEqual(ki._evaluate(obj2),None)
    self.assertEqual(ki._evaluate(obj1).keys(),[1,2])
    # explicit
    #  same as implicit for non-methods
    ki.kw.AcquisitionType= 'explicit'
    self.assertEqual(fi._evaluate(obj2),'id')
    self.assertEqual(fi._evaluate(obj1),None)
    self.assertEqual(ki._evaluate(obj2).keys(),kw.keys())
    self.assertEqual(ki._evaluate(obj1).keys(),kw.keys())
    #  now check methods
    fi.id_.Name= 'fid'; ki.kw.Name= 'fkw'
    self.assertEqual(fi._evaluate(obj2),'id')
    self.assertEqual(fi._evaluate(obj1),None)
    self.assertEqual(ki._evaluate(obj2),None)
    self.assertEqual(ki._evaluate(obj1).keys(),kw.keys())

    ## call types
    # call -- already checked
    # return
    fi.id_.CallType= 'return'
    self.assertEqual(fi._evaluate(obj2), obj1.fid)
    # ignore
    fi.id_.CallType= 'ignore'
    self.assertEqual(fi._evaluate(obj2), None)
    fi.id_.CallType= 'call'

    ## IgnoreExceptions
    fi.id_.IgnoreExceptions= 0
    self.assertRaises(AttributeError,fi._evaluate,obj1)
    self.assertEqual(fi._evaluate(obj2),'id')

  def test_ExpressionEvaluator(self):
    ki= self.ki; obj2= self.obj2
    ee= ExpressionEvaluator(); ee.id= 'ee'
    ki._setObject(ee.id,ee); ee= ki._getOb(ee.id)
    ee.manage_changeProperties(Expression= 'python: (3,4,)')
    self.assertEqual(ki._evaluate(obj2).keys(),OOSet((1,2,3,4)).keys())
    # ignore
    ee.manage_changeProperties(IgnorePredicate= 'python: 3 in value')
    self.assertEqual(ki._evaluate(obj2).keys(),OOSet((1,2,)).keys())
    # ignore - call it
    ee.manage_changeProperties(IgnorePredicate= 'python: lambda v: 3 in v')
    # normalize
    ee.manage_changeProperties(Expression= 'python: (4,)')
    ee.manage_changeProperties(Normalizer= 'python: (0,) + value')
    self.assertEqual(ki._evaluate(obj2).keys(),OOSet((0,1,2,4,)).keys())
    # normalize - call it
    ee.manage_changeProperties(Normalizer= 'python: lambda v: (0,) + v')
    self.assertEqual(ki._evaluate(obj2).keys(),OOSet((0,1,2,4,)).keys())
    # method
    ee.manage_changeProperties(Expression= "python: lambda object: object.kw")
    self.assertEqual(ki._evaluate(obj2).keys(),OOSet((0,1,2,)).keys())
    ## combine
    # 'union' - already tested
    # 'useFirst'
    ki.CombineType= 'useFirst'
    self.assertEqual(ki._evaluate(obj2).keys(),OOSet((1,2,)).keys())

  def test_TypeChecking(self):
    fi= self.fi; obj= self.obj2
    # numeric
    fi.TermType= 'numeric'
    obj.id= 1; self.assertEqual(fi._evaluate(obj),1)
    obj.id= '1'; self.assertEqual(fi._evaluate(obj),1)
    obj.id= '1.0'; self.assertEqual(fi._evaluate(obj),1.0)
    obj.id= '1.0+'; self.assertRaises(Exception,fi._evaluate,obj)
    # string
    fi.TermType= 'string'
    obj.id= 1; self.assertEqual(fi._evaluate(obj),'1')
    obj.id= '1'; self.assertEqual(fi._evaluate(obj),'1')
    obj.id= obj; self.assertRaises(Exception,fi._evaluate,obj)
    # unicode
    fi.TermType= 'ustring'
    obj.id= u'1'; self.assertEqual(fi._evaluate(obj),u'1')
    obj.id= '1'; self.assertEqual(fi._evaluate(obj),u'1')
    # integer
    fi.TermType= 'integer'
    obj.id= 1; self.assertEqual(fi._evaluate(obj),1)
    obj.id= '1'; self.assertEqual(fi._evaluate(obj),1)
    obj.id= 1.1; self.assertEqual(fi._evaluate(obj),1)
    # DateTime
    fi.TermType= 'DateTime'; now= DateTime()
    obj.id= now; self.assertEqual(fi._evaluate(obj),now)
    obj.id= '1'; self.assertRaises(Exception,fi._evaluate,obj)
    # DateTimeInteger
    fi.TermType= 'DateTimeInteger'
    obj.id= now; v = fi._evaluate(obj)
    self.assert_(isinstance(v, int))
    self.assert_(abs(v-now._t) <= 1)
    # DateInteger
    fi.TermType= 'DateInteger'
    obj.id = DateTime('1000-01-01')
    v = fi._evaluate(obj)
    self.assert_(isinstance(v, int))
    self.assertEqual(v, 400000)
    # tuple
    fi.TermType= 'tuple'
    fi.TermTypeExtra= 'n(su)d'
    obj.id= (1,('1',u'1'),now); self.assertEqual(fi._evaluate(obj),obj.id)
    fi.TermTypeExtra+= 'n'
    self.assertRaises(Exception,fi._evaluate,obj)
    fi.TermTypeExtra= fi.TermTypeExtra[:-2]
    self.assertRaises(Exception,fi._evaluate,obj)
    # instance
    fi.TermType= 'instance'
    b= obj.aq_base; cl= b.__class__
    fi.TermTypeExtra= '%s.%s' % (cl.__module__,cl.__name__)
    obj.id= b; self.assertEqual(fi._evaluate(obj),b)
    obj.id= '1'; self.assertRaises(Exception,fi._evaluate,obj)
    # expression
    fi.TermType= 'expression checked'
    fi.TermTypeExtra= 'python: 1'
    self.assertEqual(fi._evaluate(obj),1)
    fi.TermTypeExtra= 'python: lambda v: 1'
    self.assertEqual(fi._evaluate(obj),1)

    ## term copy
    fi.TermType= 'instance'
    fi.TermTypeExtra= '%s._Object' % __name__
    b= _Object()
    obj.id= b; self.assert_(fi._evaluate(obj) is b)
    fi.TermCopy= 'shallow'
    v= fi._evaluate(obj)
    self.assertEqual(v,b)
    self.assert_(v is not b)
    fi.TermCopy= 'deep'
    b.l= []
    v= fi._evaluate(obj)
    self.assertEqual(v,b)
    self.assert_(v.l is not b.l)

  def test_Terms(self):
    # normalize term
    ki= self.ki; obj= self.obj1
    ki.NormalizeTerm= 'python: lambda value: value-1'
    self.assertEqual(ki._evaluate(obj).keys(),OOSet((0,1)).keys())
    # stop term
    ki.StopTermPredicate= 'python: value == 1'
    self.assertEqual(ki._evaluate(obj).keys(),OOSet((1,)).keys())

  def test_IntegerOptimization(self):
    fi= self.fi
    for t in 'integer DateTimeInteger DateInteger'.split():
      fi.TermType = t
      fi.clear()
      self.assert_(isinstance(fi._index, IOBTree))


  def test_len(self):
    fi = self.fi; obj = self.obj2
    self.assertEqual(len(fi), 0)
    fi.index_object(1, obj)
    self.assertEqual(len(fi), 1)
    fi.index_object(2, obj)
    self.assertEqual(len(fi), 1)
    obj.id = 'id2'
    fi.index_object(2, obj)
    self.assertEqual(len(fi), 2)

  def test_FieldIndex(self):
    fi= self.fi; obj= self.obj2
    # index_object
    fi.index_object(1,obj)
    self.assertEqual(fi.numObjects(),1)
    self.assertEqual(len(fi),1)
    # simple succeeding search
    r,i= fi._apply_index({'id' : 'id'})
    self.assertEqual(i,fi.id)
    self.assertEqual(r.keys(),[1])
    self._check(fi, 'id', '1')
    # simple failing search
    r,i= fi._apply_index({'id' : ''})
    self.assertEqual(i,fi.id)
    self.assertEqual(r.keys(), [])
    # or search
    q = ('','id',)
    r,i= fi._apply_index({'id':q})
    self.assertEqual(i,fi.id)
    self.assertEqual(r.keys(), [1])
    self._check(fi, q, '1')
    # empty or search
    r,i= fi._apply_index({'id' : ()})
    self.assertEqual(i,fi.id)
    self.assertEqual(r.keys(), [])
    # range searches
    q = {'query' : ('a','z'), 'range' : 'min:max'}
    r,i= fi._apply_index({'id':q})
    self.assertEqual(i,fi.id)
    self.assertEqual(r.keys(), [1])
    self._check(fi, q, '1')
    q = {'query' : ('a',), 'range' : 'min'}
    r,i= fi._apply_index({'id':q})
    self.assertEqual(i,fi.id)
    self.assertEqual(r.keys(), [1])
    self._check(fi, q, '1')
    q = {'query' : ('z',), 'range' : 'max'}
    r,i= fi._apply_index({'id':q})
    self.assertEqual(i,fi.id)
    self.assertEqual(r.keys(), [1])
    self._check(fi, q, '1')
    r,i= fi._apply_index({'id' : {'query' : ('a','i'), 'range' : 'min:max'}})
    self.assertEqual(i,fi.id)
    self.assertEqual(r.keys(), [])
    r,i= fi._apply_index({'id' : {'query' : ('j','z'), 'range' : 'min:max'}})
    self.assertEqual(i,fi.id)
    self.assertEqual(r.keys(), [])
    r,i= fi._apply_index({'id' : {'query' : ('j',), 'range' : 'min'}})
    self.assertEqual(i,fi.id)
    self.assertEqual(r.keys(), [])
    r,i= fi._apply_index({'id' : {'query' : ('i',), 'range' : 'max'}})
    self.assertEqual(i,fi.id)
    self.assertEqual(r.keys(), [])
    # simple and search
    r,i= fi._apply_index({'id' : {'query' : ('id',), 'operator' : 'and'}})
    self.assertEqual(i,fi.id)
    self.assertEqual(r.keys(), [1])
    # multi and search
    r,i= fi._apply_index({'id' : {'query' : ('id','id',), 'operator' : 'and'}})
    self.assertEqual(i,fi.id)
    self.assertEqual(r.keys(), [1])
    # empty and search
    r= fi._apply_index({'id' : {'query' : (), 'operator' : 'and'}})
    self.assertEqual(r,None)
    # failing and search
    r,i= fi._apply_index({'id' : {'query' : ('id','',), 'operator' : 'and'}})
    self.assertEqual(i,fi.id)
    self.assertEqual(r.keys(), [])
    # reindex
    obj.id= 'id1'
    fi.index_object(1,obj)
    self.assertEqual(fi.numObjects(),1)
    self.assertEqual(len(fi),1)
    # unindex
    fi.unindex_object(1)
    self.assertEqual(fi.numObjects(),0)
    self.assertEqual(len(fi),0)

  def test_RangeIndex(self):
    ri= self.ri; obj= self.obj2
    # index_object
    ri.index_object(1,obj)
    self.assertEqual(ri.numObjects(),0)
    obj.rlow = 10; ri.index_object(1,obj)
    self.assertEqual(ri.numObjects(),0)
    obj.rhigh = 20; ri.index_object(1,obj)
    self.assertEqual(ri.numObjects(),1)
    obj.rlow = obj.rhigh = 15; ri.index_object(2,obj)
    self.assertEqual(ri.numObjects(),2)
    # search
    r,i = ri._apply_index({'ri': 9})
    self.assertEqual(i,ri.id)
    self.assertEqual(r.keys(), [])
    r,i = ri._apply_index({'ri': 15})
    self.assertEqual(i,ri.id)
    self.assertEqual(r.keys(), [1,2])
    self._check(ri, 15, '12')
    r,i = ri._apply_index({'ri': 20})
    self.assertEqual(i,ri.id)
    self.assertEqual(r.keys(), [1])
    self._check(ri, 20, '1')
    self.assertEqual(len(ri), 2)
    # boundary emulation
    ri.BoundaryNames = ('low','high')
    r = ri._apply_index({'low': {'query':15, 'range':'min'},})
    self.assertEqual(r, None)
    r = ri._apply_index({'low':{'query':15, 'range':'min'},
                         'high':{'query':16, 'range':'max'},
                         })
    self.assertEqual(r, None)
    r,i = ri._apply_index({'low':{'query':15, 'range':'min'},
                         'high':{'query':15, 'range':'max'},
                         })
    self.assertEqual(i,ri.id)
    self.assertEqual(r.keys(), [1,2])
    # unindex object
    ri.unindex_object(1)
    self.assertEqual(len(ri), 1)
    self.assertEqual(ri.numObjects(),1)
    ri.index_object(1, obj)
    self.assertEqual(len(ri), 1)
    self.assertEqual(ri.numObjects(),2)
    ri.unindex_object(1); ri.unindex_object(2)
    self.assertEqual(len(ri), 0)
    self.assertEqual(ri.numObjects(),0)

  def test_ImproperRanges(self):
    ri= self.ri; obj= self.obj2
    ri.MinimalValue = 'python:10'; ri.MaximalValue = 'python:20'
    ri.clear()
    self._indexForRange(obj, ri)
    r,i = ri._apply_index({'ri':0}); self.assertEqual(r.keys(),[1,2])
    r,i = ri._apply_index({'ri':20}); self.assertEqual(r.keys(),[1,3])
    r,i = ri._apply_index({'ri':15}); self.assertEqual(r.keys(),[1,2,3,4])
    # check empty min
    ri.MinimalValue = ''; ri.MaximalValue = 'python:20'
    ri.clear()
    self._indexForRange(obj, ri)
    r,i = ri._apply_index({'ri':0}); self.assertEqual(r.keys(),[])
    r,i = ri._apply_index({'ri':20}); self.assertEqual(r.keys(),[1,3])
    r,i = ri._apply_index({'ri':15}); self.assertEqual(r.keys(),[1,2,3,4])
    ri.MinimalValue = 'python:10'; ri.MaximalValue = ''
    ri.clear()
    self._indexForRange(obj, ri)
    r,i = ri._apply_index({'ri':0}); self.assertEqual(r.keys(),[1,2])
    r,i = ri._apply_index({'ri':21}); self.assertEqual(r.keys(),[])
    r,i = ri._apply_index({'ri':15}); self.assertEqual(r.keys(),[1,2,3,4])
    ri.MinimalValue = ''; ri.MaximalValue = ''
    ri.clear()
    self._indexForRange(obj, ri)
    r,i = ri._apply_index({'ri':0}); self.assertEqual(r.keys(),[])
    r,i = ri._apply_index({'ri':21}); self.assertEqual(r.keys(),[])
    r,i = ri._apply_index({'ri':15}); self.assertEqual(r.keys(),[1,2,3,4])

  def test_Organisation(self):
    ri = self.ri; ri.OrganisationHighThenLow = True
    ri.clear()
    self.test_RangeIndex()
    self.test_ImproperRanges()

  def _indexForRange(self, obj, ri):
      obj.rlow = 10; obj.rhigh = 20; ri.index_object(1, obj) # unrestricted
      obj.rlow = 10; obj.rhigh = 15; ri.index_object(2, obj) # low unrestricted
      obj.rlow = 15; obj.rhigh = 20; ri.index_object(3, obj) # high unrestricted
      obj.rlow = 15; obj.rhigh = 15; ri.index_object(4, obj) # proper range

  def test_PathIndex(self):
    pi= self.pi; obj= self.obj2
    # index_object
    pi.index_object(1,obj)
    self.assertEqual(pi.numObjects(),0)
    obj.pi = 'a'; pi.index_object(1,obj)
    self.assertEqual(pi.numObjects(),1)
    obj.pi = 'a/b'; pi.index_object(2,obj)
    obj.pi = 'a/b/c'.split('/'); pi.index_object(3,obj)
    # check queries
    c = self._check
    c(pi, [()], '123')
    c(pi, {'query':[()], 'level':2}, '23')
    c(pi, {'query':[()], 'level':1, 'depth':1}, '2')
    c(pi, {'query':[()], 'level':None}, '123')
    c(pi, {'query':[()], 'level':-1}, '123')
    c(pi, 'a', '123')
    c(pi, 'b', '')
    c(pi, 'x', '')
    c(pi, {'query':'b', 'level':1}, '23')
    c(pi, {'query':'b', 'level':None}, '23')
    c(pi, {'query':'b/c', 'level':-1}, '3')
    c(pi, {'query':['b/c'.split('/')], 'level':-1}, '3')
    c(pi, {'query':'c', 'level':-1}, '')
    c(pi, {'query':'c', 'level':-2}, '3')
    c(pi, {'query':'a', 'depth':0}, '1')
    c(pi, {'query':'a', 'depth':1}, '2')
    c(pi, {'query':'a', 'depth':-1}, '12')
    c(pi, {'query':'a', 'depth':None}, '123')
    c(pi, {'query':[()], 'depth':-2}, '12')
    c(pi, {'query':'b', 'level':None, 'depth':-1}, '23')


  def test_ReverseOrder(self):
    fi= self.fi; obj= self.obj2
    self.assertEqual(fi.getReverseOrder(), None)
    fi.ReverseOrder = 1; fi.clear()
    # index_object
    obj.id = '1'; fi.index_object(1,obj)
    obj.id = '2'; fi.index_object(2,obj)
    self.assertEqual(tuple(fi.getReverseOrder()), ('2','1'))
    fi.unindex_object(2)
    self.assertEqual(tuple(fi.getReverseOrder()), ('1',))

  def test_Sorting(self):
    cat= self.catalog; obj= self.obj2
    cat.catalog_object(obj,'1')
    self.assertEqual(len(self.catalog(id='id', sort_on='id')),1)
    cat.catalog_object(obj,'1')

  def test_KeywordIndex(self):
    ki= self.ki; obj= self.obj2
    # index_object
    ki.index_object(1,obj)
    self.assertEqual(ki.numObjects(),1)
    self.assertEqual(len(ki),2)
    self._check(ki, 1, '1')
    # reindex_object
    self.assertEqual(ki.index_object(1,obj),0)
    obj.kw= (2,3,)
    ki.index_object(1,obj)
    self.assertEqual(ki.numObjects(),1)
    self.assertEqual(len(ki),2)
    self.assertEqual(ki.uniqueValues(),(2,3,))
    self.assertEqual(ki.uniqueValues(withLengths=1),((2,1),(3,1),))
    # index 2
    ki.index_object(2,self.obj1)
    self.assertEqual(ki.numObjects(),2)
    self.assertEqual(len(ki),3)
    self.assertEqual(ki.uniqueValues(withLengths=1),((1,1),(2,2),(3,1),))
    # unindex
    ki.unindex_object(1)
    self.assertEqual(ki.numObjects(),1)
    self.assertEqual(len(ki),2)
    self.assertEqual(ki.uniqueValues(withLengths=1),((1,1),(2,1),))
    ki.unindex_object(2)
    self.assertEqual(ki.numObjects(),0)
    self.assertEqual(len(ki),0)
    self.assertEqual(ki.uniqueValues(withLengths=1),())

  def test_KeywordIndex_scalable(self):
    cat = self.catalog._catalog
    cat.delIndex('kw')
    ki = KeywordIndex_scalable('kw'); cat.addIndex('kw', ki)
    self.ki = cat.getIndex('kw')
    self.test_KeywordIndex()

class TestFiltering(TestBase):
  test_FieldIndex = TestManagableIndex.test_FieldIndex.im_func
  test_KeywordIndex = TestManagableIndex.test_KeywordIndex.im_func
  test_KeywordIndex_scalable = TestManagableIndex.test_KeywordIndex_scalable.im_func
  test_RangeIndex = TestManagableIndex.test_RangeIndex.im_func
  test_PathIndex = TestManagableIndex.test_PathIndex.im_func

  def _check(self, index, query, should):
    if not isinstance(query, dict): query = {'query':query}
    query['isearch'] = query['isearch_filter'] = True
    rs, _ = index._apply_index({index.id:query})
    if hasattr(rs, 'asSet'): rs = rs.asSet().keys()
    self.assertEqual(''.join(map(repr, rs)), should)

class TestMatching(TestBase):
  '''test glob and regexp expansion.'''
  TermType = 'string'

  def setUp(self):
    '''
    1 -> a
    2 -> b
    3 -> ba
    4 -> bab
    5 -> c
    6 -> cb
    7 -> d\e
    '''
    TestBase.setUp(self)
    self.index = index = self.fi; obj = self.obj1
    index.TermType = self.TermType
    for i, val in enumerate(r'a b ba bab c cb d\e'.split()):
      obj.id = val
      index.index_object(i+1, obj)

  def test_glob(self):
    self._check('glob', '*', '1234567')
    self._check('glob', 'b*', '234')
    self._check('glob', '*a', '13')
    self._check('glob', 'b?', '3')
    self._check('glob', r'd\e', '7')

  def test_regexp(self):
    self._check('regexp', 'a*', '1234567')
    self._check('regexp', 'ba+', '34')
    self._check('regexp', 'b[a]+', '34')

  def test_splitPrefix(self):
    self._checkSplit('abc', 'abc')
    self._checkSplit('+', '')
    self._checkSplit('a+', '')
    self._checkSplit(r'\+', '+')
    self._checkSplit(r'\a', '\a', '')
    self._checkSplit(r'\d', '')
    self._checkSplit(r'\c', 'c', '')
    self._checkSplit(r'\\+', '')
    self._checkSplit(r'a\\+', 'a')

  def _check(self, match, pattern, result):
    i = self.index
    r = i._apply_index({i.id : {'query' : pattern, 'match':match},})[0]
    self.assertEqual(''.join(map(str, r)), result)

  def _checkSplit(self, regexp, prefix, rep=None):
    pr,rp = _splitPrefixRegexp(regexp)
    if rep is None: self.assertEqual(escape(pr) + rp, regexp)
    else: self.assertEqual(rp, rep)
    self.assertEqual(pr, prefix)

class TestMatching_Unicode(TestMatching):
  TermType = 'ustring'


class TestMatching_Filtering(TestMatching):

  def _check(self, match, pattern, result):
    i = self.index
    r = i._apply_index({i.id : {'query' : pattern, 'match':match, 'isearch':True, 'isearch_filter':True},})[0]
    if hasattr(r, 'asSet'): r = r.asSet().keys()
    self.assertEqual(''.join(map(str, r)), result)
  


class TestWordIndex(TestBase):
  def setUp(self):
    '''
    1 -> a ab abc
    2 -> b ab bca
    '''
    TestBase.setUp(self)
    obj = self.obj1; index = self.wi
    obj.wi = 'a ab abc'; index.index_object(1, obj)
    obj.wi = 'b ab bca'; index.index_object(2, obj)

  def test_Lookup(self):
    self._check('a', '1')
    self._check('ab', '12')
    self._check('A', '')
    self._check('bca', '2')
    self.assertRaises(ValueError, self._check, 'a b', '')

  def test_Matching(self):
    self._check({'query':'a*', 'match':'glob'}, '12')
    self._check({'query':'a b', 'match':'glob'}, '')
##    self.assertRaises(ValueError,
##                      self._check,
##                      {'query':'a b', 'match':'glob'},
##                      ''
##                      )

  def _check(self, query, result):
    i = self.wi
    r = i._apply_index({i.id : query,})[0]
    self.assertEqual(''.join(map(str, r.keys())), result)





class _Object:
  def __eq__(self,other):
    return isinstance(other,_Object) and self.__dict__ == other.__dict__
  def __ne__(self,other): return not (self == other)
  def __cmp__(self,other):
    if not isinstance(other,_Object): raise TypeError('type mismatch in comparison')
    return cmp(self.__dict__,other.__dict__)



def test_suite():
  tests = [
    TestManagableIndex,
    TestMatching, TestMatching_Unicode,
    TestWordIndex,
    ]
  if IFilter is not None:
    tests.extend([TestFiltering, TestMatching_Filtering])
  return genSuite(*tests)


if __name__ == '__main__':
  runSuite(test_suite())
