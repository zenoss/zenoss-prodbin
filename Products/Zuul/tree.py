from zope.interface import implements
from zope.component import adapts

from Products.ZenUtils.json import json
from Products.Zuul.interfaces import ITreeNode, ISerializableFactory


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


class SerializableTreeFactory(object):
    implements(ISerializableFactory)
    adapts(ITreeNode)

    def __init__(self, root):
        self.root = root

    def __call__(self):
        obj = {}
        for attr in dir(self.root):
            if attr.startswith('_'):
                continue
            val = getattr(self.root, attr)
            try:
                json(val)
            except TypeError, e:
                # We can't deal with it, just move on
                continue
            obj[attr] = val
        if self.root.leaf:
            obj['leaf'] = True
        else:
            obj['children'] = []
            for childNode in self.root.children:
                serializableFactory = ISerializableFactory(childNode)
                obj['children'].append(serializableFactory())
        return obj

