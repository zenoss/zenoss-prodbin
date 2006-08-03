# Copyright (C) 2004 by Dr. Dieter Maurer, Eichendorffstr. 23, D-66386 St. Ingbert, Germany
# see "LICENSE.txt" for details
#       $Id: TestBase.py,v 1.3 2004/08/04 19:29:12 dieter Exp $
'''Test base class.

The 'AdvancedQuery' tests use 'ZopeTestCase'.
You must install this package separately (under 'lib/python/Testing').
You can get 'ZopeTestCase' from Zope.org.
'''

from unittest import TestSuite, makeSuite

from Acquisition import Implicit

from Testing.ZopeTestCase import ZopeTestCase, installProduct

installProduct('ZCatalog', 1)
installProduct('ManagableIndex', 1)
installProduct('PluginIndexes', 1)

class TestCase(ZopeTestCase):
  _indexType = 'Managable FieldIndex'
  _ReverseOrder = 0
  _stringType = 0

  def afterSetUp(self):
    folder = self.folder
    folder.manage_addProduct['ZCatalog'].manage_addZCatalog('Catalog','')
    catalog = self.catalog = folder.Catalog
    catalog.manage_addIndex('I1', self._indexType)
    catalog.manage_addIndex('I2', self._indexType)
    if self._ReverseOrder:
      indexes = catalog._catalog.indexes
      idx = indexes['I1']; idx.ReverseOrder = 1; idx.clear()
      idx = indexes['I2']; idx.ReverseOrder = 1; idx.clear()
    if self._stringType:
      indexes = catalog._catalog.indexes
      idx = indexes['I1']; idx.TermType = 'string'; idx.clear()
      idx = indexes['I2']; idx.TermType = 'string'; idx.clear()
    self._addObject(folder, 1, 'a', 'A')
    self._addObject(folder, 2, 'b', 'A')
    self._addObject(folder, 3, 'a', 'B')
    self._addObject(folder, 4, 'b', 'B')
    self._addObject(folder, 5, None, 'A')
    self._addObject(folder, 6, 'c', None)

  def _addObject(self, dest, id, a1, a2):
    id = `id`
    setattr(dest, id, _Object(id, a1, a2)); obj = getattr(dest, id)
    obj.indexObject()

  def _checkQuery(self, query, should):
    '''check that the result *query* equals *should*.

    *should* is a sequence of digits (representing ids).
    '''
    C = self.catalog
    return self._check(C.evalAdvancedQuery(query), should)

  def _check(self, result, should, order=True):
    c = self.catalog._catalog
    ids = [c.paths[r.data_record_id_] for r in result]
    if order: ids.sort()
    self.assertEqual(''.join(ids), should)



class _Object(Implicit):
  def __init__(self, id, a1, a2):
    self.id = id
    if a1 is not None: self.I1 = a1
    if a2 is not None: self.I2 = a2

  def indexObject(self):
    self.Catalog.catalog_object(self, uid=self.id)


def getSuite(*testClasses, **kw):
  prefix= kw.get('prefix','test')
  return TestSuite([makeSuite(cl,prefix) for cl in testClasses])
  
