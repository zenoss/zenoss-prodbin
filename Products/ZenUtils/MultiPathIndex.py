from types import StringType, ListType, TupleType
import logging
LOG = logging.getLogger('ZenUtils.MultiPathIndex')

from Globals import DTMLFile

from Products.PluginIndexes.PathIndex.PathIndex import PathIndex
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

class MultiPathIndex(PathIndex):
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

        if not self._unindex.has_key(docid):
            self._unindex[docid] = set()
            self._length.change(1)


        for path in paths:
            if not isinstance(path, (StringType, TupleType, ListType)):
                raise TypeError(
                    'path value must be a tuple of strings')
            if isinstance(path, (ListType, TupleType)):
                path = '/'+ '/'.join(path[1:])
            comps = filter(None, path.split('/'))
            for i in range(len(comps)):
                self.insertEntry(comps[i], docid, i)
            self._unindex[docid].add(path)

        return 1

    def unindex_object(self, docid):
        """ hook for (Z)Catalog """

        if not self._unindex.has_key(docid):
            # That docid isn't indexed.
            return

        for item in self._unindex[docid]:
            comps =  item.split('/')

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
