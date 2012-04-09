###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from contextlib import contextmanager
from functools import wraps, partial

import transaction
from ZODB.serialize import ObjectReader

__all__ = ["gc_cache_every", "gc_cache_every_decorator"]


class AutoGCObjectReader(ObjectReader):
    """
    ZODB has semipeculiar behavior wherein the object cache is only garbage
    collected at the transaction boundaries. If, within a transaction, one
    wishes to read a number of objects greater than the configured object cache
    size, the cache, and therefore memory, will simply grow with each read
    object.

    This makes sense, when you think about it. Removing cached objects out from
    under existing references could have horrible effects, so it is only safe
    when beginning a new transaction (or aborting an existing one).
    Unfortunately, we have several cases where we need to read an enormous
    number of objects within a transaction, but don't need to write anything.

    This class replaces a ZODB.Connection.Connection's existing ObjectReader.
    It will garbage-collect the cache every n objects. To enforce integrity, it
    will also abort any open transaction after cleaning the cache. It is safe
    ONLY when you are certain that the open transaction has not modified any
    objects.
    """
    _orig_reader = None
    _counter = 0
    _chunk_size = 1000

    def __init__(self, orig_reader, chunk_size=1000):
        self._counter = 0
        self._orig_reader = orig_reader
        self._conn = orig_reader._conn
        self._cache = orig_reader._cache
        self._factory = orig_reader._factory
        self._chunk_size = chunk_size

    def garbage_collect_cache(self):
        self._conn.sync()
        self._counter = 0

    def load_persistent(self, oid, klass):
        if self._counter >= self._chunk_size:
            self.garbage_collect_cache()
        ob = ObjectReader.load_persistent(self, oid, klass)
        self._counter += 1
        return ob

    def get_original(self):
        return self._orig_reader


def _normal_to_auto(connection, chunk_size=1000):
    """
    Replace the ObjectReader on a Connection with an AutoGCObjectReader.
    """
    if not isinstance(connection._reader, AutoGCObjectReader):
        connection._reader = AutoGCObjectReader(connection._reader,
                                            chunk_size=chunk_size)

def _auto_to_normal(connection):
    """
    Uninstall an AutoGCObjectReader from a Connection, replacing it with the
    original ObjectReader.
    """
    if isinstance(connection._reader, AutoGCObjectReader):
        try:
            connection._reader.garbage_collect_cache()
        finally:
            connection._reader = connection._reader.get_original()


@contextmanager
def gc_cache_every(chunk_size=1000, db=None):
    """
    Temporarily replace the ObjectReaders on the current database with
    AutoGCObjectReaders.

    WARNING: Will abort any open transaction!
    """
    db._connectionMap(
        partial(_normal_to_auto, chunk_size=chunk_size))
    try:
        yield
    finally:
        db._connectionMap(_auto_to_normal)


def gc_cache_every_decorator(chunk_size=1000, db=None):
    """
    Temporarily replace the ObjectReaders on the current database with
    AutoGCObjectReaders.

    WARNING: Will abort any open transaction!
    """
    def decorator(f):
        @wraps(f)
        def inner(*args, **kwargs):
            with gc_cache_every(chunk_size, db):
                return f(*args, **kwargs)
        return inner
    return decorator
