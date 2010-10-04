import unittest
from Products.Five import zcml
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenUtils.orm import nested_transaction
from Products.ZenUtils.tests.orm import ORMTestCase

from ..guids import Guid

class TestGuidsTable(ORMTestCase):
    _tables = (Guid,)

    def test_creation(self):
        myguid = Guid(guid='a'*36)
        myguid2 = Guid(guid='b'*36)
        with nested_transaction() as session:
            session.add_all([myguid, myguid2])
        results = self.session.query(Guid).all()
        self.assertEqual(results, [myguid, myguid2])
        self.assertEqual(myguid.id, 1)
        self.assertEqual(myguid2.id, 2)

    def test_deletion(self):
        myguid = Guid(guid='a'*36)
        myguid2 = Guid(guid='b'*36)
        myguid3 = Guid(guid='c'*36)
        with nested_transaction() as session:
            session.add_all([myguid, myguid2, myguid3])
        with nested_transaction() as session:
            session.delete(myguid2)
        results = self.session.query(Guid).all()
        self.assertEqual(results, [myguid, myguid3])
        self.assertEqual(myguid.id, 1)
        self.assertEqual(myguid3.id, 3)
        myguid4 = Guid(guid='d'*36)
        with nested_transaction() as session:
            session.add_all([myguid4])
        self.assertEqual(myguid4.id, 4)


class TestGuidUpdates(BaseTestCase, ORMTestCase):

    _tables = (Guid,)

    def setUp(self):
        BaseTestCase.setUp(self)
        ORMTestCase.setUp(self)
        zcml.load_string("""
        <configure xmlns="http://namespaces.zope.org/zope">
            <adapter
                for="Products.ZenModel.Device.Device"
                provides="Products.ZenUtils.guid.interfaces.IGUIDManager"
                factory="Products.ZenUtils.guid.guid.GUIDManager"
                />
            <adapter
                for="Products.ZenUtils.guid.interfaces.IGloballyIdentifiable"
                provides="Products.ZenUtils.guid.interfaces.IGlobalIdentifier"
                factory="Products.ZenUtils.guid.guid.GlobalIdentifier"
                />
            <include package="Products.Five" file="event.zcml" />
            <subscriber handler="Products.ZenUtils.guid.event.registerGUIDToPathMapping"/>
            <subscriber handler="Products.ZenUtils.guid.event.refireEventOnObjectAddOrMove"/>
            <subscriber handler="Products.ZenUtils.guid.event.refireEventOnObjectBeforeRemove"/>
            <subscriber handler="Products.ZenChain.guids.updateTableOnGuidEvent"/>
        </configure>
        """)

    def tearDown(self):
        ORMTestCase.tearDown(self)
        BaseTestCase.tearDown(self)

    def test_new_guid(self):
        dev = self.dmd.Devices.createInstance('newdevice')
        guid = dev._guid
        result = self.session.query(Guid).one()
        self.assertEqual(result.guid, guid)

    def test_delete_guid(self):
        before = set(self.session.query(Guid).all())
        dev = self.dmd.Devices.createInstance('newdevice')
        guid = dev._guid
        dev.deleteDevice()
        result = set(self.session.query(Guid).all())
        self.assertEqual(result, before)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.makeSuite(TestGuidsTable))
    suite.addTests(unittest.makeSuite(TestGuidUpdates))
    return suite
