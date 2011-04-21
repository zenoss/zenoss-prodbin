###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from StringIO import StringIO
from copy import copy
from pprint import pprint

import Globals
import zope.component

from Products.ZenTestCase.BaseTestCase import BaseTestCase

from Products.ZenCollector.interfaces import ICollector, ICollectorPreferences
from Products.ZenCollector.tests.testConfig import MyCollector, MyPrefs
from Products.ZenStatus.NetworkModel import NetworkModel


class BaseNetworkModelTestCase(BaseTestCase):

    def setUp(self):
        self.daemon = MyCollector()
        self.daemon._prefs = MyPrefs()
        self.name = "collectorName"
        self.daemon._prefs.options.name = self.name
        self.daemon._prefs.options.cycle = True # Allow _saveTopology to work

        zope.component.provideUtility(self.daemon, ICollector)
        self.network = NetworkModel(loadCache=False)

    def loadNetwork(self, graphString):
        self.network.reloadCache( StringIO(graphString) )

    def dumpNetwork(self):
        fd = StringIO()
        self.network._saveTopology(fd)
        return fd.getvalue()

    def showRouteTree(self):
        nodes = self.network.topology.nodes()
        nodes.remove(self.name)
        print
        print "Shortest routes"
        for endpoint in sorted(nodes):
            print self.network.getRoute(endpoint)
        print
        print "Displaying ALL edges"
        pprint( sorted(self.network.topology.edges()) )
        print


class TestNetworkModel(BaseNetworkModelTestCase):

    def testLoadNetwork(self):
        # Sanity check our internal routines
        graph = """<?xml version="1.0" encoding="utf-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">
  <graph edgedefault="undirected" id="">
      <node id="10.175.211.10" />
      <node id="10.175.213.9" />
  </graph>
</graphml>"""
        self.loadNetwork(graph)

    def testSameRoute(self):
        endpoint = '192.0.32.10' # example.com

        # Now add the route
        ttls = [self.name, '10.68.17.18', endpoint]
        added = self.network.updateTopology(copy(ttls))
        self.assertEqual(added, True, "Unable to add a route")

        # Update with the same route
        added = self.network.updateTopology(copy(ttls))
        self.assertEqual(added, False, "Updated the exact same route")

    def testRouteAddition(self):
        endpoint = '192.0.32.10' # example.com

        # What if the endpoint isn't in the topology
        route = self.network.getRoute(endpoint)
        self.assertEqual(route, [], "Found a route to an endpoint that doesn't exist")

        # Now add the route
        ttls = [self.name, '204.12.34.211',
                '10.68.17.18', '*', '67.148.20.90', '*', '*', '*', '*', 
                endpoint]
        added = self.network.updateTopology(ttls)
        self.assertEqual(added, True, "Unable to add a route")

        route = self.network.getRoute(endpoint)
        self.assertEqual(len(route), 5)

    def testRouteLoops(self):
        endpoint = '192.0.32.10' # example.com
        duplicate = '10.15.20.25'
        ttls = [self.name, duplicate,
                '10.68.17.18', '*', duplicate, endpoint]

        added = self.network.updateTopology(ttls)
        self.assertEqual(added, True, "Unable to add a route")

        route = self.network.getRoute(endpoint)
        self.assertEqual(route, [self.name, duplicate, endpoint],
                         "Didn't deduplicate gws to endpoint")

    def testSimpleCycle(self):
        """
        networkx allows for cycles and multi-graphs, which we
        don't want but allow to happen.
        The graph can be updated manually to fix anything egregious.
        """
        endpoint = '192.0.32.10' # example.com

        # Add the first route
        gw = '10.68.17.18'
        ttls = [self.name, gw, endpoint]
        added = self.network.updateTopology(ttls)

        # Change the gateway
        newgw = '10.20.17.18'
        ttls = [self.name, newgw, endpoint]
        added = self.network.updateTopology(copy(ttls))

        route = self.network.getRoute(endpoint)
        self.assertEqual(route, ttls)

    def testComplexCycle(self):
        endpoint = '192.0.32.10' # example.com

        # Add the first route
        gw = '10.68.17.18'
        ttls = [self.name, gw, endpoint]
        added = self.network.updateTopology(ttls)

        # Change the gateway
        newgw = '10.20.17.18'
        ttls = [self.name, newgw, endpoint]
        added = self.network.updateTopology(copy(ttls))

        # Whoa Nelly! Total network re-org!
        endpoint2 = '192.0.32.11'
        ttls = [self.name, gw, endpoint2]
        added = self.network.updateTopology(copy(ttls))

        ttls = [self.name, newgw, gw, endpoint]
        added = self.network.updateTopology(copy(ttls))

        # Note that the shortest path isn't necessarily the
        # *only* path.
        route = self.network.getRoute(endpoint)
        #self.assertEqual(route, ttls,
        #                 "Didn't update route to new topology")


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestNetworkModel))
    return suite
