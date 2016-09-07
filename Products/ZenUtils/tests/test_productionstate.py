##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


'''
Note that this is meant to be run from zopecctl using the "test" option. If you
would like to run these tests from python, simply to the following:

    python ZenUtils/Version.py
'''
import unittest
from zope.interface import implements
from Products.Five import zcml

from OFS.SimpleItem import SimpleItem
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from zope.component import provideHandler

from ..productionstate.interfaces import IProdStateManager
from ..guid.interfaces import IGloballyIdentifiable

class ProductionStateable(object):
    implements(IGloballyIdentifiable)
    def __init__(self, id, parent):
        self.id = id
        self.parent = parent
    def unrestrictedTraverse(self, path):
        return self.parent.unrestrictedTraverse(path)
    def getPrimaryUrlPath(self):
        return self.absolute_url_path()

class TestProductionState(BaseTestCase):

    def afterSetUp(self):
        super(TestProductionState, self).afterSetUp()
        self.ob = ProductionStateable('prodstateable', self.dmd)
        self.dmd._setOb(self.ob.id, self.ob)
        self.aq_ob = self.dmd.prodstateable
        
    def test_productionstate(self):
        # Create a ProdStateManager
        manager = IProdStateManager(self.dmd)

        # Test defaults
        prodstate = manager.getProductionState(self.ob)
        premwprodstate = manager.getPreMWProductionState(self.ob)
        self.assertEqual(prodstate, 1000)
        self.assertEqual(premwprodstate, 1000)

        # Test setting production state
        manager.setProductionState(self.ob, 400)
        prodstate = manager.getProductionState(self.ob)
        self.assertEqual(prodstate, 400)
        self.assertEqual(premwprodstate, 1000)

        # Test setting Pre-MW production state
        manager.setPreMWProductionState(self.ob, 400)
        prodstate = manager.getProductionState(self.ob)
        premwprodstate = manager.getPreMWProductionState(self.ob)
        self.assertEqual(prodstate, 400)
        self.assertEqual(premwprodstate, 400)

def test_suite():
    return unittest.makeSuite(TestProductionState)
