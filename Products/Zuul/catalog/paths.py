###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

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
        for comp in chain(
            dev.os.interfaces.objectValuesGen(),
            dev.os.ipservices.objectValuesGen(),
            dev.os.winservices.objectValuesGen(),
            dev.os.processes.objectValuesGen(),
            dev.os.software.objectValuesGen()
            ):
            paths.extend(devicePathsFromComponent(comp))
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

