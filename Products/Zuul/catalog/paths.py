##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from itertools import chain
from zope.interface import implements
from zope.component import adapts
from Products.ZenRelations.ToOneRelationship import ToOneRelationship
from interfaces import IPathReporter, IGloballyIndexed

def relPath(obj, relname):
    paths = set()
    rel = getattr(obj, relname, None)
    if rel:
        obid = obj.getId()
        remoteName = rel.remoteName()
        if isinstance(rel, ToOneRelationship):
            obs = (rel.obj,)
        else:
            obs = rel.objectValuesGen()
        for ob in obs:
            if ob is None:
                continue
            path = ob.getPrimaryPath()
            paths.add(path + (remoteName, obid))
    return list(paths)


def devicePathsFromComponent(comp):
    c_paths = IPathReporter(comp).getPaths()
    return [path + ('device',) for path in c_paths[1:]]


class DefaultPathReporter(object):
    implements(IPathReporter)
    adapts(IGloballyIndexed)

    def __init__(self, context):
        self.context = context

    def getPaths(self):
        return [self.context.getPhysicalPath()]


class DevicePathReporter(DefaultPathReporter):
    def getPaths(self):
        paths = super(DevicePathReporter, self).getPaths()
        dev = self.context
        paths.extend(relPath(dev, 'location'))
        paths.extend(relPath(dev, 'systems'))
        paths.extend(relPath(dev, 'groups'))
        return paths



class ServicePathReporter(DefaultPathReporter):
    def getPaths(self):
        paths = super(ServicePathReporter, self).getPaths()
        paths.extend(relPath(self.context, 'serviceclass'))
        return paths


class InterfacePathReporter(DefaultPathReporter):
    def getPaths(self):
        paths = super(InterfacePathReporter, self).getPaths()
        for ip in self.context.ipaddresses.objectValuesGen():
            paths.extend(relPath(ip, 'network'))
        return paths


class ProcessPathReporter(DefaultPathReporter):
    def getPaths(self):
        paths = super(ProcessPathReporter, self).getPaths()
        paths.extend(relPath(self.context, 'osProcessClass'))
        return paths


class ProductPathReporter(DefaultPathReporter):
    def getPaths(self):
        paths = super(ProductPathReporter, self).getPaths()
        paths.extend(relPath(self.context, 'productClass'))
        return paths
