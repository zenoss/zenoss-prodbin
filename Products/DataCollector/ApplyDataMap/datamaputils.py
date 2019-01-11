import logging
import sys

from six import string_types
from zope.event import notify

from Products.DataCollector.plugins.DataMaps import MultiArgs
from Products.Zuul.catalog.events import IndexingEvent


log = logging.getLogger("zen.ApplyDataMap")

MISSINGNO = object()


def _check_the_locks(datamap, device):
    if datamap._directive:
        if (
            datamap._directive in ['update', 'rebuild', 'remove']
            and _locked_from_updates(device)
        ):
            datamap._directive = 'update_locked'

        elif (
            datamap._directive in ['rebuild', 'remove']
            and _locked_from_deletion(device)
        ):
            datamap._directive = 'delete_locked'


def _locked_from_updates(obj):
    try:
        if obj.isLockedFromUpdates():
            return True
    except AttributeError:
        log.warn('_locked_from_updates: object is not lockable')
    return False


def _locked_from_deletion(obj):
    try:
        if obj.isLockedFromDeletion():
            return True
    except AttributeError:
        log.warn('_locked_from_deletion: object is not lockable')
    return False


def _evaluate_legacy_directive(datamap):
    '''Translate legacy directives
    '''
    for attr, directive in directive_map.items():
        if hasattr(datamap, attr):
            if getattr(datamap, attr):
                datamap._directive = directive
            else:
                datamap._directive = 'nochange'
            delattr(datamap, attr)

    return datamap


directive_map = {
    '_add': 'add',
    'remove': 'remove',
    '_remove': 'remove',
    '_update': 'update',
    '_rebuild': 'rebuild',
    '_nochange': 'nochange',
}


def _objectmap_to_device_diff(object_map, obj):
    '''given an ObjectMap and Object
    returns a dict of attribute: decoded value
    from the ObjectMap that do not match the Object
    '''
    diff = (
        _attribute_diff(obj, attr, value)
        for attr, value in object_map.iteritems()
    )
    diff = filter(None, diff)
    return {k: v for k, v in diff}


def _attribute_diff(obj, attr, value):
    '''Return the attribute, and decoded value if they differ
    '''
    value_prime = _get_attr_value(obj, attr)
    value = _sanitize_value(value, obj)

    if value != value_prime:
        return (attr, value)
    else:
        return None


def _get_attr_value(obj, attr):
    if attr.startswith('set'):
        try:
            getter = getattr(obj, 'get' + attr[3:])
            value = getter()
        except AttributeError:
            log.warn(
                "getter method not found: object=%s, attribute=%s",
                obj.id, attr
            )
            return MISSINGNO
    else:
        value = getattr(obj, attr, MISSINGNO)

    return _sanitize_value(value, obj)


def _sanitize_value(value, obj):
    if isinstance(value, string_types):
        try:
            return _decode_value(value, obj)
        except UnicodeDecodeError:
            # We don't know what to do with this, so don't set the value
            log.exception('unable to decode value')
            raise

    if isinstance(value, MultiArgs):
        value = value.args

    return value


def _decode_value(value, obj):
    # This looks confusing, and it is. The scenario is:
    #   A collector gathers some data as a raw byte stream,
    #   but really it has a specific encoding specified by
    #   by the zCollectorDecoding zProperty. Say, latin-1 or
    #   utf-16, etc. We need to decode that byte stream to get
    #   back a UnicodeString object. But, this version of Zope
    #   doesn't like UnicodeString objects for a variety of
    #   fields, such as object ids, so we then need to convert
    #   that UnicodeString back into a regular string of bytes,
    #   and for that we use the system default encoding, which
    #   is now utf-8.
    try:
        codec = obj.zCollectorDecoding
    except AttributeError:
        codec = sys.getdefaultencoding()

    value = value.decode(codec)
    value = value.encode(sys.getdefaultencoding())
    return value


def _update_object(obj, diff):
    '''given an object map, with a _diff containing sanitized attributes
    update the object
    '''
    log.debug('_update_object: obj=%s, diff=%s', obj, diff)

    for attrname, value in diff.items():
        attr = getattr(obj, attrname, MISSINGNO)
        if attr is MISSINGNO:
            continue
        elif callable(attr):
            _update_callable_attribute(attr, value)
        else:
            setattr(obj, attrname, value)

    try:
        obj.index_object()
    except AttributeError:
        pass

    notify(IndexingEvent(obj))
    obj.setLastChange()

    return True


def _update_callable_attribute(attr, value):
    try:
        try:
            attr(*value) if isinstance(value, tuple) else attr(value)
        except ValueError:
            value = (value,)
            attr(*value)
    except Exception:
        log.exception(
            'Error in _update_callable_attribute. failed to set %s.%s%s',
            attr.__module__, attr.__name__, value
        )
