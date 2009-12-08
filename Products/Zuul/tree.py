

from zope.interface import implements
from zope.component import adapts
from Products.Zuul.interfaces import ITreeNode


class TreeNode(object):
    implements(ITreeNode)

    def __init__(self, ob):
        self._object = ob

    @property
    def id(self):
        raise NotImplementedError

    @property
    def text(self):
        return self._object.titleOrId()

    @property
    def children(self):
        raise NotImplementedError

    def __repr__(self):
        return "<%s(id=%s)>" % (self.__class__.__name__, self.id)
