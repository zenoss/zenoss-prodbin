from unittest import TestCase
from mock import Mock, MagicMock, sentinel, patch

from base64 import b64encode

from Products.DataCollector.plugins.DataMaps import ObjectMap
from Products.ZenModel.Device import Device

from ..datamaputils import (
    MultiArgs,
    log,
    MISSINGNO,
    _check_the_locks,
    _locked_from_updates,
    _locked_from_deletion,
    _evaluate_legacy_directive,
    _objectmap_to_device_diff,
    _attribute_diff,
    _sanitize_value,
    _get_attr_value,
    _update_object,
    _update_callable_attribute,
)


log.setLevel('DEBUG')

PATH = {'src': 'Products.DataCollector.ApplyDataMap.datamaputils'}


class GetSetObject():
    def __init__(self):
        self.Attr = sentinel.original

    def setAttr(self, value):
        self.Attr = value

    def getAttr(self):
        return self.Attr


class Test_check_the_locks(TestCase):

    def setUp(t):
        t.datamap = Mock(name='datamap')
        t.device = Mock(name='device')
        t.device.isLockedFromUpdates.return_value = False
        t.device.isLockedFromDeletion.return_value = False

    def test_update_update_locked(t):
        t.datamap._directive = 'update'
        t.device.isLockedFromUpdates.return_value = True
        _check_the_locks(t.datamap, t.device)
        t.assertEqual(t.datamap._directive, 'update_locked')

    def test_update_update_unlocked(t):
        t.datamap._directive = 'update'
        t.device.isLockedFromUpdates.return_value = False
        _check_the_locks(t.datamap, t.device)
        t.assertEqual(t.datamap._directive, 'update')

    def test_rebuild_update_locked(t):
        t.datamap._directive = 'rebuild'
        t.device.isLockedFromUpdates.return_value = True
        _check_the_locks(t.datamap, t.device)
        t.assertEqual(t.datamap._directive, 'update_locked')

    def test_remove_update_locked(t):
        t.datamap._directive = 'remove'
        t.device.isLockedFromUpdates.return_value = True
        _check_the_locks(t.datamap, t.device)
        t.assertEqual(t.datamap._directive, 'update_locked')

    def test_rebuild_delte_locked(t):
        t.datamap._directive = 'remove'
        t.device.isLockedFromDeletion.return_value = True
        _check_the_locks(t.datamap, t.device)
        t.assertEqual(t.datamap._directive, 'delete_locked')

    def test_rebuild_delte_unlocked(t):
        t.datamap._directive = 'remove'
        t.device.isLockedFromDeletion.return_value = False
        _check_the_locks(t.datamap, t.device)
        t.assertEqual(t.datamap._directive, 'remove')

    def test_remove_delet_locked(t):
        t.datamap._directive = 'rebuild'
        t.device.isLockedFromDeletion.return_value = True
        _check_the_locks(t.datamap, t.device)
        t.assertEqual(t.datamap._directive, 'delete_locked')


class Test__locked_from_updates(TestCase):

    def test_locked(t):
        obj = Mock(spec=['isLockedFromUpdates'])
        obj.isLockedFromUpdates.return_value = True
        ret = _locked_from_updates(obj)
        t.assertEqual(ret, True)

    def test_unlocked(t):
        obj = Mock(spec=['isLockedFromUpdates'])
        obj.isLockedFromUpdates.return_value = False
        ret = _locked_from_updates(obj)
        t.assertEqual(ret, False)

    def test_not_lockable(t):
        '''if isLockedFromUpdates is not defined, it cannot be locked
        '''
        obj = Mock(spec=[])
        ret = _locked_from_updates(obj)
        t.assertEqual(ret, False)


class Test__locked_from_deletion(TestCase):

    def test_locked(t):
        obj = Mock(spec=['isLockedFromDeletion'])
        obj.isLockedFromDeletion.return_value = True
        ret = _locked_from_deletion(obj)
        t.assertEqual(ret, True)

    def test_unlocked(t):
        obj = Mock(spec=['isLockedFromDeletion'])
        obj.isLockedFromDeletion.return_value = False
        ret = _locked_from_deletion(obj)
        t.assertEqual(ret, False)

    def test_not_lockable(t):
        '''if isLockedFromDeletion is not defined, it cannot be locked
        '''
        obj = Mock(spec=[])
        ret = _locked_from_deletion(obj)
        t.assertEqual(ret, False)


class Test__evaluate_legacy_directive(TestCase):

    def setUp(t):
        t.object_map = ObjectMap()

    def test_legacy__add_flag(t):
        t.object_map._add = True
        ret = _evaluate_legacy_directive(t.object_map)
        t.assertEqual(ret._directive, 'add')
        t.assertEqual(t.object_map._directive, 'add')

    def test_legacy_remove_flag(t):
        t.object_map.remove = True
        _evaluate_legacy_directive(t.object_map)
        t.assertEqual(t.object_map._directive, 'remove')

    def test_legacy__remove_flag(t):
        t.object_map._remove = True
        _evaluate_legacy_directive(t.object_map)
        t.assertEqual(t.object_map._directive, 'remove')

    def test_legacy__update_flag(t):
        t.object_map._update = True
        _evaluate_legacy_directive(t.object_map)
        t.assertEqual(t.object_map._directive, 'update')

    def test_legacy__rebuild_flag(t):
        t.object_map._rebuild = True
        _evaluate_legacy_directive(t.object_map)
        t.assertEqual(t.object_map._directive, 'rebuild')

    def test_legacy__nochange_flag(t):
        t.object_map._nochange = True
        _evaluate_legacy_directive(t.object_map)
        t.assertEqual(t.object_map._directive, 'nochange')

    def test_legacy_false_nochange(t):
        t.object_map._update = False
        _evaluate_legacy_directive(t.object_map)
        t.assertEqual(t.object_map._directive, 'nochange')


class Test_objectmap_to_device_diff(TestCase):

    def test_no_change(t):
        '''Unchanged objects return an empty dict
        '''
        object_map = ObjectMap(data={
            'id': 'objectid',
            '_underbar_are_ignored': True,
            'attr_a': 'attribute a',
            'attr_b': sentinel.attr_b,
        })
        device = Device(object_map.id)
        device.attr_a = 'attribute a'
        device.attr_b = sentinel.attr_b
        device.missing_from_object_map = 'not_checked_by_diff'

        ret = _objectmap_to_device_diff(object_map, device)
        t.assertEqual(ret, {})
        t.assertFalse(ret)

    def test_changed(t):
        '''changed objects
        return a dict of the attribute name and sanitized value
        Including any new values added by the map
        '''
        object_map = ObjectMap(data={
            'id': 'objectid',
            'attr_a': 'new value',
            'attr_b': sentinel.attr_b,
            'attr_c': sentinel.new_attr_c,
        })
        device = Device(object_map.id)
        device.attr_a = 'attribute a'
        device.attr_b = sentinel.attr_b

        ret = _objectmap_to_device_diff(object_map, device)

        t.assertEqual(
            ret,
            {'attr_a': 'new value', 'attr_c': sentinel.new_attr_c}
        )
        t.assertTrue(ret)

    def test_object_missing_attr(t):
        pass

    def test_callable_attribute_changed(t):
        obj = GetSetObject()
        object_map = ObjectMap(data={'setAttr': sentinel.new})
        ret = _objectmap_to_device_diff(object_map, obj)
        t.assertEqual(ret, {'setAttr': sentinel.new})

    def test_callable_attribute_unchanged(t):
        obj = GetSetObject()
        object_map = ObjectMap(data={'setAttr': sentinel.original})
        ret = _objectmap_to_device_diff(object_map, obj)
        t.assertEqual(ret, {})

    def test_multiargs_attribute_changed(t):
        value = MultiArgs(sentinel.a, ['a', 'b'], {'a': 1})
        obj = ObjectMap(data={'id': 'objectid', 'attr_a': value})
        obj = Device('objectid')
        obj.attr_a = MultiArgs(sentinel.a, ['a', 'b'], {'a': 1})
        new_value = MultiArgs(sentinel.a, ['a', 'b'], {'a': 1, 'b': 2})
        object_map = ObjectMap(data={'id': 'objectid', 'attr_a': new_value})

        ret = _objectmap_to_device_diff(object_map, obj)
        t.assertEqual(ret, {'attr_a': new_value.args})

    def test_multiargs_attribute_unchanged(t):
        value = MultiArgs(sentinel.a, ['a', 'b'], {'a': 1})
        obj = Device('objectid')
        obj.attr_a = value
        object_map = ObjectMap(data={'id': 'objectid', 'attr_a': value})

        ret = _objectmap_to_device_diff(object_map, obj)
        t.assertEqual(ret, {})

    def test_encoding(t):
        enc_maps = {
            'ascii': ObjectMap(
                {'a': 'abcdefg', 'b': 'hijklmn', 'c': 'opqrstu'}
            ),
            'utf-8': ObjectMap({
                'a': u'\xe0'.encode('utf-8'),
                'b': u'\xe0'.encode('utf-8'),
                'c': u'\xe0'.encode('utf-8')
            }),
            'latin-1': ObjectMap({
                'a': u'\xe0'.encode('latin-1'),
                'b': u'\xe0'.encode('latin-1'),
                'c': u'\xe0'.encode('latin-1')
            }),
            'utf-16': ObjectMap({
                'a': u'\xff\xfeabcdef'.encode('utf-16'),
                'b': u'\xff\xfexyzwow'.encode('utf-16'),
                # (water, z, G clef), UTF-16 encoded, little-endian with BOM
                'c': '\xff\xfe\x34\x6c\x7a\x00\x34\xd8\x13\xdd'
            })
        }

        for enc, objectmap in enc_maps.items():
            obj = Device('oid')
            obj.a, obj.b, obj.c = None, None, None
            obj.zCollectorDecoding = enc
            diff = _objectmap_to_device_diff(objectmap, obj)
            for key, val in diff.items():
                t.assertEqual(val, getattr(objectmap, key).decode(enc))


class Test_attribute_diff(TestCase):

    def test_changed(t):
        obj = Mock(name='object')
        obj.attr = sentinel.original
        ret = _attribute_diff(obj, 'attr', sentinel.new)
        t.assertEqual(ret, ('attr', sentinel.new))
        t.assertTrue(ret)

    def test_unchanged(t):
        obj = Mock(name='object')
        obj.attr = sentinel.original
        ret = _attribute_diff(obj, 'attr', sentinel.original)
        t.assertEqual(ret, None)

    def test_callable_changed(t):
        obj = GetSetObject()
        ret = _attribute_diff(obj, 'setAttr', sentinel.new)
        t.assertEqual(ret, ('setAttr', sentinel.new))

    def test_callable_unchanged(t):
        obj = GetSetObject()
        ret = _attribute_diff(obj, 'setAttr', sentinel.original)
        t.assertEqual(ret, None)

    def test_multiargs_changed(t):
        obj = Device('objectid')
        value = MultiArgs(sentinel.a, ['a', 'b'], {'a': 1})
        obj.attr_a = value
        new_value = MultiArgs(sentinel.a)
        ret = _attribute_diff(obj, 'attr_a', new_value)
        t.assertTupleEqual(ret, ('attr_a', new_value.args))

    def test_multiargs_unchanged(t):
        obj = Device('objectid')
        value = MultiArgs(sentinel.a, ['a', 'b'], {'a': 1})
        obj.attr_a = value
        ret = _attribute_diff(obj, 'attr_a', value)
        t.assertEqual(ret, None)


class Test_get_attr_value(TestCase):

    def test_set_methods(t):
        '''given an attribute that starts with 'set'
        returns the value from the attribute's 'get' method
        '''
        obj = GetSetObject()
        obj.setAttr(sentinel.attribute)

        value = _get_attr_value(obj, 'Attr')

        t.assertEqual(value, sentinel.attribute)

    def test_naked_attribute(t):
        '''non set values are returned from the attribute
        '''
        obj = sentinel.object
        obj.attribute = sentinel.attribute

        value = _get_attr_value(obj, 'attribute')

        t.assertEqual(value, sentinel.attribute)

    def test_missing_attribute(t):
        '''missing attributes return MISSINGNO sentinel value
        '''
        obj = sentinel.object
        ret = _get_attr_value(obj, 'undefined')
        t.assertEqual(ret, MISSINGNO)

    def test_missing_getter_method(t):
        obj = GetSetObject()
        obj.id = 'testobj'  # for logging
        ret = _get_attr_value(obj, 'setUndefined')
        t.assertEqual(ret, MISSINGNO)


class Test_sanitize_value(TestCase):

    def test_handles_strings(t):
        value = 'some_string'
        ret = _sanitize_value(value, sentinel.obj)
        t.assertEqual(ret, value)

    def test_decodes_strings(t):
        original_str = 'some_string'
        value = b64encode(original_str)
        obj = Mock(zCollectorDecoding='base64')

        ret = _sanitize_value(value, obj)

        t.assertEqual(ret, original_str)

    def test_handles_MultiArgs(t):
        args = (sentinel.a, 'some_string', {'a': 1})
        value = MultiArgs(*args)
        ret = _sanitize_value(value, sentinel.obj)
        t.assertEqual(ret, args)

    @patch('{src}._decode_value'.format(**PATH), autspec=True)
    def test_raises_UnicodeDecodeError(t, _decode_value):
        _decode_value.side_effect = UnicodeDecodeError('', '', 0, 0, '')
        value = 'some string'
        with t.assertRaises(UnicodeDecodeError):
            _sanitize_value(value, sentinel.obj)


class Test_decode_value(TestCase):

    def test_decodes_strings(t):
        original_str = 'some_string'
        value = b64encode(original_str)
        obj = Mock(zCollectorDecoding='base64')

        ret = _sanitize_value(value, obj)

        t.assertEqual(ret, original_str)


class Test_update_object(TestCase):

    def test_update(t):
        obj = Device('deviceid')
        obj.attr = sentinel.a
        diff = {'attr': 'sanitized sentinel.b'}

        ret = _update_object(obj, diff)

        t.assertEqual(obj.attr, 'sanitized sentinel.b')
        t.assertTrue(ret)

    @patch('{src}._update_callable_attribute'.format(**PATH), autospec=True)
    def test_callable_attributes(t, _update_callable_attribute):
        obj = GetSetObject()
        obj.id = 'object_id'
        obj.Attr = None
        obj.setLastChange = Mock()
        diff = {'setAttr': 'sanitized sentinel.value'}

        obj.setAttr('x')
        t.assertEqual(obj.Attr, 'x')

        _update_object(obj, diff)

        _update_callable_attribute.assert_called_with(
            obj.setAttr, 'sanitized sentinel.value'
        )
        obj.setLastChange.assert_called_with()

    def test_ignores_undefined_attributes(t):
        '''does not add attributes that do not exist on the target
        '''
        obj = Device('deviceid')
        obj.attr = sentinel.a
        new_attr = 'undefined'
        diff = {'attr': 'sanitized sentinel.b', new_attr: 'new attr'}

        ret = _update_object(obj, diff)

        t.assertEqual(obj.attr, 'sanitized sentinel.b')
        t.assertFalse(hasattr(obj, new_attr))
        t.assertTrue(ret)


class Test_update_callable_attribute(TestCase):

    def test_uses_set_method_to_update(t):
        obj = Mock(name='object', spec_set=['setAttr'])
        value = (('a', 'b'), 'args', ['list', 'x'], {'a', 'dict'}, )
        _update_callable_attribute(obj.setAttr, value)
        obj.setAttr.assert_called_with(*value)
        obj.setAttr.assert_called_with(
            ('a', 'b'), 'args', ['list', 'x'], {'a', 'dict'}
        )

    def test_updates_multiargs_attributes(t):
        obj = Mock(name='object', spec_set=['setAttr'])
        value = (sentinel.a, sentinel.b, sentinel.c)
        _update_callable_attribute(obj.setAttr, value)
        obj.setAttr.assert_called_with(sentinel.a, sentinel.b, sentinel.c)

    @patch('{src}.log'.format(**PATH), autospec=True)
    def test_handles_exceptions(t, log):
        obj = Mock(name='object', spec_set=['setAttr'])

        def setAttr(*args):
            raise Exception()
        obj.setAttr = setAttr
        value = (('a', 'b'), 'args', ['list', 'x'], {'a', 'dict'}, )

        _update_callable_attribute(obj.setAttr, value)

        log.exception.assert_called_with(
            'Error in _update_callable_attribute. failed to set %s.%s%s',
            obj.setAttr.__module__, obj.setAttr.__name__, value
        )
