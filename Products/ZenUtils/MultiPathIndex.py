###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from types import ListType, TupleType
import logging
LOG = logging.getLogger('ZenUtils.MultiPathIndex')

from Globals import DTMLFile

from ExtendedPathIndex import ExtendedPathIndex
from Products.PluginIndexes.common import safe_callable

def _isSequenceOfSequences(seq):
    if not seq: 
        return False
    if not isinstance(seq, (TupleType, ListType)):
        return False
    for item in seq:
        if not isinstance(item, (TupleType, ListType)):
            return False
    return True

def _recursivePathSplit(seq):
    if isinstance(seq, (TupleType, ListType)):
        return map(_recursivePathSplit, seq)
    if '/' in seq: 
        return seq.split('/')
    else: 
        return seq

class MultiPathIndex(ExtendedPathIndex):
    """
    A path index that is capable of indexing multiple paths per object.
    """
    meta_type = "MultiPathIndex"

    def getIndexSourceNames(self):
        """ return names of indexed attributes """
        return (self.id, )

    def index_object(self, docid, obj ,threshold=100):
        """ hook for (Z)Catalog """

        f = getattr(obj, self.id, None)
        if f is not None:
            if safe_callable(f):
                try:
                    paths = f()
                except AttributeError:
                    return 0
            else:
                paths = f
        else:
            try:
                paths = obj.getPhysicalPath()
            except AttributeError:
                return 0

        if not paths: return 0

        paths = _recursivePathSplit(paths)

        if not _isSequenceOfSequences(paths):
            paths = [paths]

        # Safest to clear out all for this object first
        if self._unindex.has_key(docid):
            self.unindex_object(docid)
        self._unindex[docid] = set()
        self._length.change(1)

        for path in paths:
            if isinstance(path, (list, tuple)):
                path = '/'+ '/'.join(path[1:])
            comps = filter(None, path.split('/'))
            parent_path = '/' + '/'.join(comps[:-1])

            for i in range(len(comps)):
                self.insertEntry(comps[i], docid, i)

            # Add terminator
            self.insertEntry(None, docid, len(comps)-1, parent_path, path)

            self._unindex[docid].add(path)

        return 1

    def unindex_object(self, docid):
        """ hook for (Z)Catalog """

        if not self._unindex.has_key(docid):
            return

        def unindex(comp, level, docid=docid, parent_path=None,
                    object_path=None):
            try:
                self._index[comp][level].remove(docid)

                if not self._index[comp][level]:
                    del self._index[comp][level]

                if not self._index[comp]:
                    del self._index[comp]
                # Remove parent_path and object path elements
                if parent_path is not None:
                    self._index_parents[parent_path].remove(docid)
                    if not self._index_parents[parent_path]:
                        del self._index_parents[parent_path]
                if object_path is not None:
                    del self._index_items[object_path]
            except KeyError:
                # Failure
                pass

        for path in self._unindex[docid]:
            if not path.startswith('/'):
                path = '/'+path
            comps =  path.split('/')
            parent_path = '/'.join(comps[:-1])


            for level in range(len(comps[1:])):
                comp = comps[level+1]

                try:
                    self._index[comp][level].remove(docid)

                    if not self._index[comp][level]:
                        del self._index[comp][level]

                    if not self._index[comp]:
                        del self._index[comp]
                except KeyError:
                    # We've already unindexed this one.
                    pass

            # Remove the terminator
            level = len(comps[1:])
            comp = None
            unindex(comp, level-1, parent_path=parent_path, object_path=path)

        self._length.change(-1)
        del self._unindex[docid]

    manage = manage_main = DTMLFile('dtml/manageMultiPathIndex', globals())
    manage_main._setName('manage_main')


manage_addMultiPathIndexForm = DTMLFile('dtml/addMultiPathIndex', globals())

def manage_addMultiPathIndex(self, id, REQUEST=None, RESPONSE=None, 
                             URL3=None):
    """
    Add a MultiPathIndex.
    """
    return self.manage_addIndex(id, 'MultiPathIndex', extra=None,
                                REQUEST=REQUEST, RESPONSE=RESPONSE,
                                URL1=URL3)
