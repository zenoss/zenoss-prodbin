###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Products.Five.browser import BrowserView
from Products.ZenUtils.json import json
from Products.ZenUtils.Utils import formreq
from Products.AdvancedQuery import MatchGlob


class DeviceNames(BrowserView):
    """
    Provides device names for autocompleter population.

    Adapts DeviceClasses.
    """
    @json
    @formreq
    def __call__(self, query=''):
        """
        @param query: A glob by which to filter device names
        @type query: str
        @return: A JSON representation of a list of ids
        @rtype: "['id1', 'id2', 'id3']"
        """
        brains = self.context.dmd.Devices.deviceSearch.evalAdvancedQuery(
                                MatchGlob('id', query.rstrip('*') + '*'))
        deviceIds = [b.id for b in brains]
        deviceIds.sort(lambda x, y: cmp(x.lower(), y.lower()))
        return deviceIds


class ComponentPaths(BrowserView):
    """
    Get component paths and names associated with a given device or group of
    devices.

    Adapts DeviceClasses.
    """
    @json
    @formreq
    def __call__(self, deviceIds=()):
        """
        @param deviceIds: One ore more device ids under which components should be
        sought
        @type deviceIds: str
        @return: A JSON representation of a list of tuples describing components
        under devices specified
        @rtype: "[('/path/to/comp1', 'comp1'), ...]"
        """
        paths = set()
        if isinstance(deviceIds, basestring):
            deviceIds = [deviceIds]
        for devId in deviceIds:
            d = self.context.findDevice(devId)
            if d:
                dPathLen = len(d.getPrimaryId()) + 1
                for comp in d.getMonitoredComponents():
                    paths.add((comp.getPrimaryId()[dPathLen:], comp.name()))
        paths = list(paths)
        paths.sort(lambda x,y: cmp(x[0], y[0]))
        return paths


class GraphIds(BrowserView):
    """
    Get a list of the graph defs available for the given device
    and component.

    Adapts DeviceClasses.
    """
    @json
    @formreq
    def __call__(self, deviceIds=(), componentPaths=()):
        """
        @param deviceIds: One ore more device ids under which graphs should be
        sought
        @type deviceIds: str, list
        @param componentPaths: Path(s) to components under which graphs should
        be sought
        @type componentPaths: str, list
        @return: A JSON representation of a list of ids
        @rtype: "['id1', 'id2', 'id3']"
        """
        graphIds = set()
        if isinstance(deviceIds, basestring):
            deviceIds = [deviceIds]
        if isinstance(componentPaths, basestring):
            componentPaths = [componentPaths]
        if not componentPaths:
            componentPaths = ('',)
        for devId in deviceIds:
            thing = self.context.findDevice(devId)
            if thing:
                for compPath in componentPaths:
                    compPath = compPath or ''
                    parts = compPath.split('/')
                    for part in parts:
                        if part:
                            if hasattr(thing, part):
                                thing = getattr(thing, part)
                            else:
                                break
                    else:
                        for t in thing.getRRDTemplates():
                            for g in t.getGraphDefs():
                                graphIds.add(g.id)
        graphIds = list(graphIds)
        graphIds.sort()
        return graphIds


class ServiceList(BrowserView):
    """
    Get a list of id and descriptions for a live search

    """
    @json
    @formreq
    def __call__(self, dataRoot='serviceclasses'):
        """
        @param dataRoot: The name of the relation under which services should
        be sought
        @type dataRoot: str
        @return: A JSON representation of a list of service ids
        @rtype: "['id1', 'id2', ...]"
        """
        liveSearchList = []
        for srv in self.context.getSubInstancesGen(rel='serviceclasses'):
            if getattr(srv, 'description', None):
                liveSearchList.append('%s [%s]' % (srv.id, srv.description))
            else:
                liveSearchList.append(srv.id)
        return liveSearchList


class EventClassNames(BrowserView):
    """
    Get a list of all event classes that match the filter.
    """
    @json
    @formreq
    def __call__(self):
        """
        @return: A JSON representation of a list of paths
        @rtype: "['/path/1', '/path/2', ...]"
        """
        orgs = self.context.dmd.Events.getSubOrganizers()
        paths = ['/'.join(x.getPrimaryPath()) for x in orgs]
        paths = [p.replace('/zport/dmd','') for p in paths]
        return paths


class OrganizerNames(BrowserView):
    """
    Return the organizer names to which this user has access
    """
    @json
    @formreq
    def __call__(self, dataRoot="Devices"):
        """
        @return: A JSON representation of a list of organizers
        @rtype: "['/Systems/Sys1', '/Groups/Group1', ...]"
        """
        root = self.context.dmd.getDmdRoot(dataRoot)
        return root.getOrganizerNames()


