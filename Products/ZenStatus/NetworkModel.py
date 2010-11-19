###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """NetworkModel

Maintain the state of the network topology and associated meta-data.

"""

import time
import os
import re
import logging
log = logging.getLogger("zen.networkModel")

from networkx import DiGraph, shortest_path, minimum_spanning_tree
from networkx.readwrite import read_graphml, write_graphml
from networkx.exception import NetworkXError

import Globals
from zope.component import queryUtility

from Products.ZenCollector.interfaces import ICollector

from Products.ZenUtils.Utils import zenPath


# TODO: Examine how bad the memory usage is and see if it's worth it
#       to convert the node labels to being integers rather than strings --
#       or if that even affects the memory usage.
#from Products.ZenUtils.IpUtil import ipToDecimal

class NetworkModel(object):

    def __init__(self, loadCache=True):
        self._preferences = queryUtility(ICollector)._prefs

        self.notModeled = set()
        self.traceTimedOut = set()

        self.hopToCloudRules = {}

        self.downDevices = set()

        self.topology = None
        if loadCache:
            self.reloadCache()
        else:
            self._newTopology()

    def _newTopology(self):
        """
        Create a blank new topology
        """
        collectorName = self._preferences.options.monitor
        self.topology = DiGraph(name=collectorName,
                                creationTime=time.time())

    def getRoute(self, endpoint):
        """
        Given an endpoint name, get the route to it.
        If the endpoint doesn't exist, return an empty route.

        @parameter endpoint: name of the device
        @type endpoint: string
        @returns: list of devices from the collector to the endpoint
        @rtype: array
        """
        if endpoint not in self.topology:
            return []

        # Since we don't allow cycles or multiple references,
        # the shortest path should also be the ONLY path
        try:
            route = shortest_path(self.topology,
                                       self._preferences.options.name,
                                       endpoint)
        except NetworkXError:
            # Node is in the topology but not connected
            route = []

        return route

    def showRoute(self, endpoint):
        """
        Print the route from the collector to the endpoint device IP.

        @parameter device: name of the device
        @type device: string
        """
        ip = self.resolveName(endpoint)
        if not ip:
            log.warn("The device '%s' was not found in the topology" 
                     " -- try using the IP address", endpoint)
            return
        route = self.getRoute(ip)
        if route:
            log.info("Route to %s (%s): %s", endpoint, ip, route)
        else:
            log.warn("No route for the device %s (%s) was found",
                     endpoint, ip)

    def search(self, key, criteria=None, regex=None):
        """
        Search the topology for any matches to the key.

        @parameter key:
        @type key: string
        @parameter criteria:
        @type criteria: string or callable
        """
        # Note that the data coming back from self.topology.nodes(data=True)
        # is a tuple of
        #   (key, data)
        if criteria is not None and not callable(criteria):
            functor = lambda keyData: keyData[1].get(key) == criteria
        elif regex is not None:
            cregex = re.compile(regex)
            functor = lambda keyData: cregex.search(keyData[1].get(key, ''))
        else:
            return []
        return filter(functor, self.topology.nodes_iter(data=True))

    def resolveName(self, deviceName):
        """
        Given a device name, resolve to an IP address using only the
        information in the topology.
        """
        if deviceName in self.topology:
            return deviceName

        matches = self.search('name', regex=deviceName)
        if matches:
            return matches[0]

    def saveTopology(self):
        """
        Checkpoint the topology to disk to preserve changes even
        in the face of crashes etc.
        """
        now = time.time()
        checkpointAge = (now - self.topologySaveTime) / 60
        if checkpointAge > self._preferences.options.savetopominutes:
            self._saveTopology()

    def _getTopoCacheName(self):
        # The graphml library supports automatic compression of the file
        # if the filename ends in .gz or .bz2
        if self._preferences.options.topofile:
            return self._preferences.options.topofile
        return zenPath('perf/Daemons/%s.topology.graphml' % self._preferences.options.monitor)

    def reloadCache(self, topologyCache=None):
        """
        Restore any previously saved topology or create a new one.
        """
        if topologyCache is None:
            topologyCache = self._getTopoCacheName()
        if hasattr(topologyCache, 'read') or os.path.exists(topologyCache):
            try:
                start = time.time()
                self.topology = read_graphml(topologyCache)
                log.info("Read %s nodes and %s edges from topology cache in %0.1f s.",
                         self.topology.number_of_nodes(),
                         self.topology.number_of_edges(),
                         time.time() - start)
            except IOError, ex:
                log.warn("Unable to read topology file %s because %s",
                         topologyCache, str(ex))
            except SyntaxError, ex:
                log.warn("Bad topology file %s: %s",
                         topologyCache, str(ex))
                try:
                    if not hasattr(topologyCache, 'read'):
                        os.rename(topologyCache, topologyCache + '.broken')
                except IOError, ex:
                    log.warn("Unable to move bad topology file out of the way: %s",
                             str(ex))

        if self.topology is None:
            self._newTopology()

        # Reset the save time to avoid saving the cache immediately
        self.topologySaveTime = time.time()

    def _saveTopology(self, topologyCache=None):
        """
        Allow the topology to be periodically saved.
        """
        if not self._preferences.options.cycle:
            # Prevent possibly trashing the cache if we're not cycling
            return

        if topologyCache is None:
            topologyCache = self._getTopoCacheName()

        if self.topology is None:
            log.debug("Empty topology -- not saving")
            return

        if not hasattr(topologyCache, 'read') and os.path.exists(topologyCache):
            try:
                os.rename(topologyCache, topologyCache + '.previous')
            except IOError, ex:
                log.warn("Unable to create backup topology file because %s",
                         str(ex))
        try:
            start = time.time()
            self._stripUncacheableMetaData()
            write_graphml(self.topology, topologyCache)
            log.info("Saved %s nodes and %s edges in topology cache in %0.1fs.",
                     self.topology.number_of_nodes(),
                     self.topology.number_of_edges(),
                     time.time() - start)
        except IOError, ex:
            log.warn("Unable to write topology file %s because %s",
                     topologyCache, str(ex))
        self.topologySaveTime = time.time()

    def _stripUncacheableMetaData(self):
        """
        The topology map carries a direct reference to tasks (ie pointers),
        which can't be persisted.
        """
        for ipAddress in self.topology.nodes_iter():
            if 'task' in self.topology.node[ipAddress]:
                del self.topology.node[ipAddress]['task']

    def disconnectedNodes(self):
        """
        Determine the list of devices to traceroute and update
        the topology map.
        """
        # Devices recently added
        if self.notModeled:
            return list(self.notModeled - self.traceTimedOut)

        # Devices added from cache, but not properly modeled
        return filter(lambda x: self.topology.degree(x) == 0 and \
                                x not in self.traceTimedOut,
                      self.topology.nodes_iter())

    def updateTopology(self, route):
        """
        Canonicalize the route, removing any cloud entries,
        and update the topology (if necessary).

        @returns: was the topology updated or not?
        @rtype: boolean
        """
        existingRoute = self.getRoute(route[-1])
        canonRoute = self._canonicalizeRoute(route)
        if existingRoute:
            if existingRoute == canonRoute:
                return False, False

        lastHop = canonRoute.pop(0)
        updated = False
        while canonRoute:
            hop = canonRoute.pop(0)

            if hop not in self.topology:
                self.topology.add_node(hop)
                updated = True

            if lastHop != hop and \
               not self.topology.has_edge(lastHop, hop):
                self.topology.add_edge(lastHop, hop)
                updated = True
            lastHop = hop

        return updated

    def makeSpanningTree(self):
        """
        Clear the existing structure and create a spanning tree.
        This is a dangerous operation.
        """
        G = minimum_spanning_tree(self.topology.to_undirected())

        # Note: to_directed() returns a directed graph --
        #       but with edges in *both* directions

        # Update with the minimum spanning tree edge list
        newEdgeList = G.edges()
        oldEdgeList = self.topology.edges()
        self.topology.remove_edges_from(oldEdgeList)
        self.topology.add_edges_from(newEdgeList)

    def _canonicalizeRoute(self, route):
        """
        Given a route, reduce it to a route that can exist in the topology
        """
        lastHop = self._preferences.options.name
        canonRoute = [lastHop]
        while route:
            hop = route.pop(0)
            if hop == '*': # Build bogus device?
                continue
            hop =  self._cloudify(hop)
            canonRoute.append(hop)
            lastHop = hop
        return canonRoute

    def _cloudify(self, hop):
        """
        If the hop is a part of the cloud, then return the cloud name.
        Else return the hop.

        If the cloud does not exist in the topology, creates it.

        @parameter hop: name or IP address
        @type hop: string
        @returns: the hop (if not a part of a cloud) or the cloud
        @rtype: string
        """
        if hop in self.topology:
            # If we've already added this into the topology, don't
            # attempt to mask it out.
            return hop

        for cloudName, regex in self.hopToCloudRules.items():
            if regex.match(hop):
                self._addCloud(cloudName)
                return cloudName
        return hop

    def _addCloud(self, cloud):
        """
        If the cloud already exists, do nothing.
        Else, create the cloud and initialize it.

        @parameter cloud: name of the cloud
        @type cloud: string
        """
        if cloud in self.topology:
            return
        self.topology.add_node(cloud, ping=False)

    def removeDevice(self, device):
        """
        Cleanly remove the device from the topology.

        @parameter device: name of the device to check
        @type device: string
        """
        if device not in self.topology:
            log.debug("Device %s not deleted as it is not in topology",
                      device)
            return

        route = self.getRoute(device)[:-1]
        lastHop = route[-1]

        neighbors = self.topology.neighbors(device)
        if lastHop in neighbors:
            neighbors.remove(lastHop)
        self.notModeled.update(neighbors)

        self.topology.remove_node(device)
        log.debug("Deleted device %s from topology", device)


    def subgraphPingNodes(self):
        """
        Prune out nodes from the topology which we don't monitor.
        This means that if we model the route x -> y -> z
        but we only ping nodes x + z, that if x and z are down
        that we associate the cause of z being down as x, rather than being
        independent.
        """
        # Based on the code from networkx for dfs_tree/dfs_successor
        G = self.topology
        seen = set()
        ignoreList = set()
        def keepNode(node):
            if node in ignoreList:
                return False
            elif 'task' not in self.topology.node[node]:
                ignoreList.add(node)
                return False
            return True
    
        tree = {}
        for root in self.topology.nodes_iter():
            if root in seen:
                continue
    
            queue = [ root ]
            lastValidRoot = None
            while queue:
                node = queue[-1]
                if node not in seen:
                    seen.add(node)
                    if keepNode(node):
                        tree[node] = []
                        lastValidRoot = node

                for w in self.topology.neighbors_iter(node):
                    if w not in seen:
                        queue.append(w)
                        if keepNode(w) and lastValidRoot:
                            tree[lastValidRoot].append(w)
                        break
                else:
                    queue.pop()
    
        return DiGraph(tree)
    
