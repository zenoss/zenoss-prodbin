from unittest import TestCase
from mock import Mock

# Breaks unittest independence due to
# ImportError: No module named CMFCore.DirectoryView
from Products.ZenHub.invalidationoid import (
    DefaultOidTransform,
    PrimaryPathObjectManager,
    IInvalidationOid,
    DeviceOidTransform,
)

from zope.interface.verify import verifyObject
from zope.component import adaptedBy


class DefaultOidTransformTest(TestCase):

    def setUp(self):
        self.obj = Mock(PrimaryPathObjectManager, autospec=True, set_spec=True)
        self.default_oid_transform = DefaultOidTransform(self.obj)

    def test_implements_IInvalidationOid(self):
        # Provides the interface
        IInvalidationOid.providedBy(self.default_oid_transform)
        # Implements the interface it according to spec
        verifyObject(IInvalidationOid, self.default_oid_transform)

    def test_adapts_PrimaryPathObjectManager(self):
        self.assertEqual(
            list(adaptedBy(DefaultOidTransform)),
            [PrimaryPathObjectManager]
        )

    def test_init(self):
        self.assertEqual(self.default_oid_transform._obj, self.obj)

    def test_transformOid(self):
        ret = self.default_oid_transform.transformOid('unmodified oid')
        self.assertEqual(ret, 'unmodified oid')


class DeviceOidTransformTest(TestCase):

    def setUp(self):
        self.obj = Mock(PrimaryPathObjectManager, autospec=True, set_spec=True)
        self.device_oid_transform = DeviceOidTransform(self.obj)

    def test_implements_IInvalidationOid(self):
        # Provides the interface
        IInvalidationOid.providedBy(self.device_oid_transform)
        # Implements the interface it according to spec
        verifyObject(IInvalidationOid, self.device_oid_transform)

    def test_init(self):
        self.assertEqual(self.device_oid_transform._obj, self.obj)

    def test_transformOid(self):
        '''returns unmodified oid, if _obj has no device attribute
        '''
        self.assertFalse(hasattr(self.obj, 'device'))
        ret = self.device_oid_transform.transformOid('unmodified oid')
        self.assertEqual(ret, 'unmodified oid')

    def test_transformOid_returns_device_oid(self):
        '''returns obj.device()._p_oid if obj.device exists
        '''
        obj = Mock(
            name='PrimaryPathObjectManager', spec=['device'], set_spec=True
        )
        device = Mock(name='device', spec=['_p_oid'], set_spec=True)
        obj.device.return_value = device

        device_oid_transform = DeviceOidTransform(obj)
        ret = device_oid_transform.transformOid('ignored oid')

        self.assertEqual(ret, obj.device.return_value._p_oid)
