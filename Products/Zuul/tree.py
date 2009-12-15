from itertools import imap
from zope.dottedname.resolve import resolve
from zope.interface import implements, Interface, implementedBy
from zope.component import adapts
from Products.Zuul.interfaces import ITreeNode, ITreeWalker, IEntityManager
from Products.Zuul.utils import safe_hasattr as hasattr, unbrain
from Products.Zuul.utils import LazySortableList
from Products.ZenModel.RRDTemplate import RRDTemplate
from Products.ZenModel.Organizer import Organizer
from Products.ZenModel.DeviceOrganizer import DeviceOrganizer
from Products.ZenModel.Device import Device
from Products.ZenModel.OSProcessClass import OSProcessClass
from Products.ZenModel.ServiceClass import ServiceClass
from Products.ZenRelations.RelSchema import ToManyCont


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
        

def _resolve_class(name):
    clsname = name + '.' + name.rsplit('.', 1)[-1]
    return resolve(clsname)


class Matcher(object):
    def __init__(self, types):
        self._blacklist = []
        self.types = []
        for t in types:
            if hasattr(t, 'implementedBy'):
                self.types.append(t)
            else:
                self.types.append(implementedBy(t))

    def blacklist(self, t):
        self._blacklist.append(t)
        
    def matches(self, target):
        bad = Matcher(self._blacklist)
        if isinstance(target, type):
            for t in self.types:
                if (t.implementedBy(target) and
                    not bad.matches(target)):
                    return True
        else:
            for t in self.types:
                if (t.providedBy(target) and
                    not bad.matches(target)):
                    return True


def _makeSpec(types):
    if isinstance(types, (tuple, list)):
        spec = Matcher(types)
    elif isinstance(types, Matcher):
        spec = types
    else:
        spec = Matcher((types,))
    return spec


class WalkerBase(object):
    implements(ITreeWalker)

    def __init__(self, context):
        self.context = context

    def children(self, types=None, depth=None):
        if types is not None:
            kids = self.rawChildren(types, depth)
        else:
            kids = self.rawChildren(depth=depth)
        for k in kids:
            yield k

    def rawChildren(self, types=(Interface,), depth=None):
        raise NotImplementedError('rawChildren must be implemented'
                                  ' by a subclass.')
    

class RecursiveWalker(WalkerBase):
    adapts(Organizer)

    def _recursive_children(self, spec, containment=True):
        for ob in self.context.objectValues():
            if spec.matches(ob):
                yield ob
        for name, schema in self.context._relations:
            if containment and not isinstance(schema, ToManyCont):
                continue
            remoteClass = _resolve_class(schema.remoteClass)
            if spec.matches(remoteClass):
                rel = getattr(self.context, name)
                for ob in rel.objectValuesGen():
                    yield ob
        
    def rawChildren(self, types=(Interface,), depth=None):
        spec = _makeSpec(types)
        if depth is not None:
            if not depth:
                raise StopIteration
            else:
                depth -= 1
        for match in self._recursive_children(spec):
            yield match
        for org in self.context.children():
            for match in ITreeWalker(org).children(spec, depth):
                yield match



class DeviceOrganizerWalker(RecursiveWalker):
    implements(ITreeWalker)
    adapts(DeviceOrganizer)

    def _catalog_search(self, catalog, index, depth):
        path = self.context.getPrimaryUrlPath()
        query = {'query':path}
        if depth is not None:
            # Need to add one to account for containing relationship
            query['depth'] = depth + 1
        brains = catalog(**{index:query})
        return brains
            
    def rawChildren(self, types=(Device,), depth=None):
        spec=_makeSpec(types)
        if spec.matches(Device):
            cat = self.context.dmd.Devices.deviceSearch
            for b in self._catalog_search(cat, 'path', depth):
                yield b
            spec.blacklist(Device)
        if spec.matches(RRDTemplate):
            cat = self.context.dmd.searchRRDTemplates
            for b in self._catalog_search(cat, 'getPhysicalPath', depth):
                yield b
            spec.blacklist(RRDTemplate)
        for ob in super(DeviceOrganizerWalker, self).rawChildren(spec, depth):
            yield ob


class RelationshipWalker(WalkerBase):
    default_types = (Interface,)
    relmap = None
    def rawChildren(self, types=None, depth=None):
        if types is None:
            types = self.default_types
        spec = _makeSpec(types)
        for interface, relname in self.relmap.iteritems():
            if spec.matches(interface):
                rel = getattr(self.context, relname)
                for ob in rel.objectValuesGen():
                    yield ob
        if depth is not None:
            if not depth:
                raise StopIteration
            else:
                depth -= 1
        for org in self.context.children():
            for match in ITreeWalker(org).children(spec, depth):
                yield match


class ProcessTreeWalker(RelationshipWalker):
    default_types = (OSProcessClass,)
    relmap = {
        OSProcessClass:'osProcessClasses'
    }


class ServiceTreeWalker(RelationshipWalker):
    default_types = (ServiceClass,)
    relmap = {
        ServiceClass:'serviceclasses'
    }


class EntityManager(object):
    implements(IEntityManager)

    def __init__(self, context):
        self.context = context

    def search(self, types=None, start=0, limit=None, orderby=None, 
                 cmp=None, key=None, reverse=False, depth=None):
        args = {'depth':depth}
        if types is not None:
            args['types'] = types
        gen = ITreeWalker(self.context).children(**args)
        l = LazySortableList(gen, orderby=orderby, cmp=cmp, key=key, 
                             reverse=reverse)
        if limit is not None:
            result = l[start:start+limit]
        else:
            result = l[start:]
        return imap(unbrain, result)
