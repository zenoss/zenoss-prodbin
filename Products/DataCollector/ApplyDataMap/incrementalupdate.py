from __future__ import absolute_import, division, print_function

import logging
from importlib import import_module

from zope.event import notify

from Products.DataCollector.plugins.DataMaps import ObjectMap
from Products.DataCollector.Exceptions import ObjectCreationError
from Products.ZenUtils.Utils import NotFound


from .datamaputils import (
    _check_the_locks,
    _evaluate_legacy_directive,
    _objectmap_to_device_diff,
    _update_object,
)
from .events import DatamapUpdateEvent


log = logging.getLogger('zen.IncrementalDataMap')  # pragma: no mutate

NOTSET = object()


class InvalidIncrementalDataMapError(Exception):
    pass


class IncrementalDataMap(object):

    _target = NOTSET
    _parent = None
    _relationship = None
    __diff = None
    changed = False

    def __init__(self, base, object_map):
        self._base = base
        self.__original_object_map = object_map

        if not isinstance(object_map, ObjectMap):
            raise InvalidIncrementalDataMapError()

        object_map = _evaluate_legacy_directive(object_map)

        self._process_objectmap(object_map)
        if not self._target_id:
            raise InvalidIncrementalDataMapError()
        self.id = self._target_id

        self._directive = getattr(object_map, '_directive', None)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.__dict__)

    def _process_objectmap(self, object_map):
        self._parent_id = getattr(object_map, 'parentId', None)
        self._target_id = getattr(object_map, 'id', None)
        self.path = getattr(object_map, 'compname', None)
        self.relname = getattr(object_map, 'relname', None)
        self.modname = getattr(object_map, 'modname', None)
        self.classname = getattr(object_map, 'classname', None)

        self._object_map = {
            k: v for k, v in object_map.iteritems()
            if k not in ['parentId', 'relname', 'id']
        }

    def apply(self):
        ret = self._directive_map[self.directive]()
        return ret

    @property
    def _directive_map(self):
        return {
            'add': self._add,
            'update': self._update,
            'remove': self._remove,
            'nochange': self._nochange,
        }

    @property
    def parent(self):
        if not self._parent:
            if self.path:
                # look up the specified component path
                try:
                    self._parent = self._base.getObjByPath(self.path)
                except NotFound:
                    self._parent = self._base
            else:
                # if compname is not specified, use the base device
                self._parent = self._base

        return self._parent

    @property
    def _relname(self):
        '''expose _relname for ADMReporter
        '''
        return self.relname

    @property
    def relationship(self):
        if not self._relationship:
            self._relationship = getattr(self.parent, self.relname)

        return self._relationship

    @property
    def target(self):
        if self._target is NOTSET:
            target = self.parent

            if self.relname:
                log.debug('target: relationship=%s', self.relationship)  # pragma: no mutate
                try:
                    target = self.relationship._getOb(self._target_id)
                except Exception:
                    log.warn('related object NOT FOUND')  # pragma: no mutate
                    target = None

            self._target = target

        return self._target

    @target.setter
    def target(self, value):
        self._target = value

    @property
    def classname(self):
        if not self._classname:
            self._classname = self.modname.split(".")[-1]

        return self._classname

    @classname.setter
    def classname(self, value):
        self._classname = value

    @property
    def directive(self):
        if not self.__directive:
            if self.target is None:
                self.directive = 'add'
            elif not self._diff:
                self.directive = 'nochange'
            else:
                self.directive = 'update'

        return self.__directive

    @directive.setter
    def directive(self, value):
        self.__directive = value
        _check_the_locks(self, self.target)

        # validate directive
        if self.__directive == 'add':
            if not self.modname:
                raise InvalidIncrementalDataMapError(
                    'adding an object requires modname'  # pragma: no mutate
                )
            if not self.relationship:
                raise ObjectCreationError(
                    'relationship not found:'  # pragma: no mutate
                    'device=%s, class=%s relationship=%s'  # pragma: no mutate
                    % (
                        self.parent.id, self.parent.__class__,
                        self.relationship,
                    )
                )

    @property
    def _directive(self):
        '''expose _directive for ADMReporter
        '''
        return self.directive

    @_directive.setter
    def _directive(self, value):
        self.directive = value

    @property
    def _diff(self):
        if self.__diff is None:
            self.__diff = _objectmap_to_device_diff(
                self._object_map, self.target
            )

        return self.__diff

    def iteritems(self):
        return self._object_map.iteritems()

    def _add(self):
        '''Add the target device to the parent relationship
        '''
        self._create_target()
        self._add_target_to_relationship()
        self.target = self.relationship._getOb(self._target_id)
        self._update()

    def _update(self):
        '''Update the target object using diff
        '''
        _update_object(self.target, self._diff)

        notify(DatamapUpdateEvent(
            self._base.dmd, self.__original_object_map, self.target
        ))

        self.changed = True

    def _remove(self):
        '''Remove the target object from the relationship
        '''
        if not self.target:
            self.changed = False
            return

        try:
            self.parent.removeRelation(self.relname, self.target)
            self.changed = True
        except AttributeError:
            self.changed = False

    def _create_target(self):
        '''create a new zodb object from the object map we were given
        '''
        mod = import_module(self.modname)
        constructor = getattr(mod, self.classname)
        self.target = constructor(self._target_id)

    def _add_target_to_relationship(self):
        if self.relationship.hasobject(self.target):
            return True

        log.debug(
            'add related object: parent=%s, relationship=%s, obj=%s',  # pragma: no mutate
            self.parent.id, self.relname, self._target_id
        )
        # either use device.addRelation(relname, object_map)
        # or create the object, then relationship._setObject(obj.id, obj)
        self.relationship._setObject(self._target_id, self.target)
        return True

    def _nochange(self):
        '''make no change if the directive is nochange
        '''
        log.debug(
            'object unchanged: parent=%s, relationship=%s, obj=%s',  # pragma: no mutate
            self.parent.id, self.relname, self._target_id
        )
