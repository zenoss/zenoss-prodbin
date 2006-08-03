# Copyright (C) 2003 by Dr. Dieter Maurer, Eichendorffstr. 23, D-66386 St. Ingbert, Germany
# see "LICENSE.txt" for details
#       $Id: TestBase.py,v 1.5 2005/09/17 08:42:03 dieter Exp $
'''Test infrastructure.'''



#######################################################################
# Hack to find our "INSTANCE_HOME" infrastructure.
# Note, that "testrunner.py" overrides "INSTANCE_HOME". Therefore,
# we look also for "TEST_INSTANCE_HOME"
from os import environ, path
import sys

def _updatePath(path,dir):
  if dir not in path: path.insert(0,dir)

_ih= environ.get('TEST_INSTANCE_HOME') or environ.get('INSTANCE_HOME')
if _ih:
  _updatePath(sys.path, path.join(_ih,'lib','python'))
  import Products; _updatePath(Products.__path__,path.join(_ih,'Products'))


#######################################################################
# Standard imports
from unittest import TestCase, TestSuite, makeSuite, TextTestRunner

from Acquisition import Explicit, Implicit
from OFS.Application import Application
from OFS.SimpleItem import SimpleItem
from Products.ZCatalog.ZCatalog import ZCatalog
from Products.ZCTextIndex.Lexicon import Lexicon, Splitter

from Products.ManagableIndex.FieldIndex import FieldIndex
from Products.ManagableIndex.KeywordIndex import KeywordIndex
from Products.ManagableIndex.RangeIndex import RangeIndex
from Products.ManagableIndex.WordIndex import WordIndex
from Products.ManagableIndex.PathIndex import PathIndex

def genSuite(*testClasses,**kw):
  prefix= kw.get('prefix','test')
  return TestSuite([makeSuite(cl,prefix) for cl in testClasses])

def runSuite(suite):
  tester= TextTestRunner()
  tester.run(suite)

def runTests(*testClasses,**kw):
  runSuite(genSuite(*testClasses,**kw))


class Lexicon(Lexicon, SimpleItem): pass

#######################################################################
# Test base class
class TestBase(TestCase):
  '''An application with a catalog with field index 'id',
  keyword index 'ki', range index 'ri', word index 'wi', path index 'pi'
  and two objects 'obj1' and 'obj2'.
  '''
  def setUp(self):
    app= Application()
    catalog= ZCatalog('Catalog')
    app._setObject('Catalog',catalog)
    self.catalog= catalog= app._getOb('Catalog')
    # create indexes -- avoid the official API because it requires
    # product setup and this takes ages
    cat= catalog._catalog
    # field
    fi= FieldIndex('id'); cat.addIndex('id',fi)
    self.fi= cat.getIndex('id')
    # keyword
    ki= KeywordIndex('kw'); cat.addIndex('kw',ki)
    self.ki= cat.getIndex('kw')
    # range
    ri= RangeIndex('ri'); cat.addIndex('ri',ri)
    self.ri = ri = cat.getIndex('ri')
    ri._delObject('ri'); ri.CombineType = 'aggregate'
    ri.addValueProvider('rlow','AttributeLookup')
    ri.addValueProvider('rhigh','AttributeLookup')
    # word
    lexicon = Lexicon(Splitter())
    app._setObject('lexicon', lexicon)
    wi = WordIndex('wi'); cat.addIndex('wi',wi)
    wi.Lexicon = 'lexicon'
    self.wi = cat.getIndex('wi')
    # path
    pi= PathIndex('pi'); cat.addIndex('pi',pi)
    self.pi= cat.getIndex('pi')
    # create objects
    self.obj1= obj1= _Object()
    obj1.kw= (1,2)
    obj1.fkw= _Caller(lambda obj: obj.kw)
    obj1.fid= _Caller(lambda obj: obj.id)
    self.obj2= obj2= _Object().__of__(obj1)
    obj2.id= 'id'

  def _check(self, index, query, should):
    rs, _ = index._apply_index({index.id:query})
    self.assertEqual(''.join(map(repr, rs.keys())), should)


#######################################################################
# Auxiliaries

class _Caller(Explicit):
  def __init__(self,f):
    self._f= f

  def __call__(self):
    return self._f(self.aq_parent)

class _Object(Implicit):
  __roles__ = None
  __allow_access_to_unprotected_subobjects__ = True
  def __cmp__(self,other):
    if not isinstance(other,_Object): raise TypeError('type mismatch in comparison')
    return cmp(self.__dict__,other.__dict__)
