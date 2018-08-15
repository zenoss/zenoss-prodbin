from unittest import TestCase
from mock import Mock, create_autospec

from Products.ZenHub.notify import (
    NotifyItem,
    BatchNotifier,
)


class NotifyItemTest(TestCase):

    def test_init(self):
        device_class_uid = 'some uuid'
        subdevices = ['list of', 'devices']

        notify_item = NotifyItem(device_class_uid, subdevices)

        self.assertEqual(notify_item.device_class_uid, device_class_uid)
        self.assertEqual(notify_item.subdevices, subdevices)
        # filtered defaults to false
        self.assertEqual(notify_item.filtered, False)
        self.assertEqual(notify_item.notify_functions, {})
        self.assertEqual(notify_item.d, None)
        # filtered defaults to false


class BatchNotifierTest(TestCase):

    def test_init(self):
        BatchNotifier()

    def test_notify_subdevices(self):
        device_class = 'device_class'
        service_uid = 'service_uid'
        notify_function = 'notify_function'
        filter = None

        bn = BatchNotifier()
        item = Mock(spec_set=NotifyItem(device_class, 'subdevices'))
        item.notify_functions = {}
        # Mock the find_or_create_item method
        bn._find_or_create_item = create_autospec(
            bn._find_or_create_item, return_value=item
        )

        bn.notify_subdevices(
            device_class, service_uid, notify_function, filter=filter
        )

        bn._find_or_create_item.assert_called_with(
            device_class, filter
        )
        self.assertEqual(item.notify_functions[service_uid], notify_function)

    def test_find_or_create_item(self):
        self.assertTrue(False)
