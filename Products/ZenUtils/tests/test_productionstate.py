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

from Acquisition import aq_base
from OFS.SimpleItem import SimpleItem
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from zope.component import provideHandler

from ..productionstate.interfaces import IProdStateManager, ProdStateNotSetError
from ..guid.interfaces import IGloballyIdentifiable, IGlobalIdentifier

class ProductionStateable(SimpleItem):
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

        zcml.load_string("""
        <configure xmlns="http://namespaces.zope.org/zope">
            <adapter
                for="Products.ZenUtils.tests.test_productionstate.ProductionStateable"
                provides="Products.ZenUtils.productionstate.interfaces.IProdStateManager"
                factory="Products.ZenUtils.productionstate.productionstate.ProdStateManager"
                />
            <adapter
                for="Products.ZenUtils.tests.test_productionstate.ProductionStateable"
                provides="Products.ZenUtils.guid.interfaces.IGUIDManager"
                factory="Products.ZenUtils.guid.guid.GUIDManager"
                />
            <include package="Products.Five" file="event.zcml" />
            <subscriber handler="Products.ZenUtils.productionstate.event.updateGUIDToProdStateMapping"/>
        </configure>
        """)

    def test_productionstate(self):
        # Create a ProdStateManager
        manager = IProdStateManager(self.dmd)

        # Test Exception
        self.assertRaises(ProdStateNotSetError, manager.getProductionState, self.ob)
        self.assertRaises(ProdStateNotSetError, manager.getPreMWProductionState, self.ob)

        # Test setting production state
        manager.setProductionState(self.ob, 400)
        prodstate = manager.getProductionState(self.ob)
        self.assertEqual(prodstate, 400)
        self.assertRaises(ProdStateNotSetError, manager.getPreMWProductionState, self.ob)

        # Test setting Pre-MW production state
        manager.setPreMWProductionState(self.ob, 400)
        prodstate = manager.getProductionState(self.ob)
        premwprodstate = manager.getPreMWProductionState(self.ob)
        self.assertEqual(prodstate, 400)
        self.assertEqual(premwprodstate, 400)

        # Test getting production state by guid
        guid = IGlobalIdentifier(self.ob).getGUID()
        self.assertEqual(manager.getProductionStateFromGUID(guid), 400)

        # Test clearing production state
        manager.clearProductionState(self.ob)
        self.assertRaises(ProdStateNotSetError, manager.getProductionState, self.ob)
        self.assertRaises(ProdStateNotSetError, manager.getPreMWProductionState, self.ob)


    def test_object_remove(self):
        newob = ProductionStateable('newprodstateable', self.dmd)
        self.dmd._setObject('newprodstateable', newob)
        manager = IProdStateManager(self.aq_ob)
        oldGuid = IGlobalIdentifier(newob).getGUID()
        manager.setProductionState(newob, 400)
        self.assertEqual(manager.getProductionState(newob), 400)
        self.dmd._delObject('newprodstateable')

        # make sure guid is still the same before checking that it was removed from the table
        newGuid = IGlobalIdentifier(newob).getGUID()
        self.assertEqual(oldGuid, newGuid)

        # guid should be removed from the table, so we should get errors trying to access them
        self.assertRaises(ProdStateNotSetError, manager.getProductionState, newob)
        self.assertRaises(ProdStateNotSetError, manager.getPreMWProductionState, newob)

    def test_device_move(self):
        source = self.dmd.Devices.createOrganizer('source')
        dest = self.dmd.Devices.createOrganizer('dest')
        dev = source.createInstance('testdevice')
        manager = IProdStateManager(self.aq_ob)
        manager.setProductionState(dev, 1)
        manager.setPreMWProductionState(dev, 2)
        source.moveDevices(dest.getOrganizerName(), 'testdevice')
        newdev = dest.devices.testdevice
        self.assertEqual(manager.getProductionState(newdev), 1)
        self.assertEqual(manager.getPreMWProductionState(newdev), 2)

    def test_fallback_migrate(self):

        # Create a ProdStateManager
        manager = IProdStateManager(self.dmd)

        # Test Exception when nothing set
        self.assertRaises(ProdStateNotSetError, manager.getProductionState, self.ob)
        self.assertRaises(ProdStateNotSetError, manager.getPreMWProductionState, self.ob)

        # Set old-style prod state and preMW prod state
        aq_base(self.ob).productionState = 400
        aq_base(self.ob).preMWProductionState = 500

        # Should be no more exception
        self.assertEqual(manager.getProductionState(self.ob), 400)
        self.assertEqual(manager.getPreMWProductionState(self.ob), 500)

        # Old attributes should be gone
        self.assertEqual(getattr(aq_base(self.ob), 'productionState', None), None)
        self.assertEqual(getattr(aq_base(self.ob), 'preMWProductionState', None), None)

def test_suite():
    return unittest.makeSuite(TestProductionState)
