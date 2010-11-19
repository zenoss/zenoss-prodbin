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

__doc__ = """TopologyCorrelatorTask

Examines the pending event queue and determines what events need to be sent.
The correlator can reschedule ping jobs to delay or obsess under stress
conditions.

The correlator is also the only job to send out events for the managedIps.

The correlator may not have all of the devices that are associated with an
IP realm or even a regular network. The implication is that two collectors
on the same server will split up the devices into two trees, neither of
which may have knowledge of the complete network topology.

This same issue occurs for layer 2 devices, which may dole out the work
to determine up/down status of connected devices over multiple collectors.

The simple case of just the Zenoss master server can be made to work, as
zenping will have full knowledge of the topology.
"""

import logging
log = logging.getLogger("zen.correlatorTask")

from networkx import dfs_tree

import Globals
import zope.interface
import zope.component

from twisted.internet import defer

from Products.ZenCollector.interfaces import IDataService,\
                                             IEventService,\
                                             IScheduledTask
from Products.ZenCollector.tasks import BaseTask,\
                                        TaskStates

from Products.ZenEvents.ZenEventClasses import Status_Ping

STATUS_EVENT = { 
                'eventClass' : Status_Ping,
                'component' : 'zenping',
                'eventGroup' : 'Ping' }

class TopologyCorrelatorTask(BaseTask):
    zope.interface.implements(IScheduledTask)

    def __init__(self,
                 taskName,
                 configId=None,
                 scheduleIntervalSeconds=60,
                 taskConfig=None,
                 daemonRef=None):
        """
        @param deviceId: the Zenoss deviceId to watch
        @type deviceId: string
        @param taskName: the unique identifier for this task
        @type taskName: string
        @param scheduleIntervalSeconds: the interval at which this task will be
               collected
        @type scheduleIntervalSeconds: int
        @param taskConfig: the configuration for this task
        @param daemonRef: a reference to the daemon
        """
        super(TopologyCorrelatorTask, self).__init__()

        # Needed for interface
        self.name = taskName
        self.configId = configId if configId else taskName
        self.state = TaskStates.STATE_IDLE
        self.interval = scheduleIntervalSeconds

        if taskConfig is None:
            raise TypeError("taskConfig cannot be None")
        self._preferences = taskConfig

        if daemonRef is None:
            raise TypeError("daemonRef cannot be None")
        self._daemon = daemonRef
        self._topology = self._daemon.network.topology
        self._downDevices = self._daemon.network.downDevices
        self._notModeled = self._daemon.network.notModeled

        self._dataService = zope.component.queryUtility(IDataService)
        self._eventService = zope.component.queryUtility(IEventService)

        self._lastErrorMsg = ''

    def doTask(self):
        """
        Traceroute from the collector to the endpoint nodes,
        with chunking.

        @return: A task to traceroute devices
        @rtype: Twisted deferred object
        """
        log.debug('---- Correlation begins ----')
        # Prune out intermediate devices that we don't ping
        pingGraph = self._daemon.network.subgraphPingNodes()

        # The subgraph() call preserves the base graph's structure (DAG), but
        # returns the connected subtrees (ie all down nodes and their connected
        # edges).  A copy(), not deepcopy() is done to the meta-data.
        downGraph = pingGraph.subgraph(self._downDevices)

        # All down-nodes are possible roots of down-trees
        rootEvents = 0
        victimEvents = 0
        for root in downGraph.nodes_iter():
            if not downGraph.predecessors(root):
                # This node is the root of subtree
                victims = dfs_tree(downGraph, source=root).nodes()
                victims.remove(root)
                rootEvents += 1
                victimEvents += len(victims)
                self._sendPingDown(root, victims)

        stats = 'Correlator sent %d root cause and %d victim events' % (
                rootEvents, victimEvents)
        log.debug(stats)
        log.debug('---- Correlation ends ----')
        return defer.succeed(stats)

    def _sendPingDown(self, root, victims):
        """
        Send ping down events for the subtree of devices rooted at the root.

        @parameter root: IP address of the root device of the downed subtree
        @type root: string
        @parameter victims: IP addresses of the consequences of the downed root device
        @type victims: array of strings
        """
        log.debug("Sending down events for %s and affected devices %s",
                  root, victims)
        task = self._topology.node[root]['task']
        self.sendPingEvent(task.pingjob, root=root)

        for victim in victims:
            task = self._topology.node[victim]['task']
            self.sendPingEvent(task.pingjob, root=root)

    def sendPingEvent(self, pj, root):
        """
        Send an event based on a ping job to the event backend.
        """
        evt = dict(device=pj.hostname,
                   ipAddress=pj.ipaddr,
                   summary=pj.message,
                   severity=pj.severity,
                   eventClass=Status_Ping,
                   eventGroup='Ping',
                   rootDevice=root,
                   component=pj.iface)
        evstate = getattr(pj, 'eventState', None)
        if evstate is not None:
            evt['eventState'] = evstate
        self._eventService.sendEvent(evt)

    def displayStatistics(self):
        """
        Called by the collector framework scheduler, and allows us to
        see how each task is doing.
        """
        nodes = self._daemon.network.topology.number_of_nodes()
        edges = self._daemon.network.topology.number_of_edges()
        down = len(self._daemon.network.downDevices)
        display = "%s nodes: %d edges: %d down: %d\n" % (
            self.name, nodes, edges, down)

        if self._lastErrorMsg:
            display += "%s\n" % self._lastErrorMsg
        return display


#if __name__=='__main__':
# TODO: Debugging tool
# TODO: read a topology file and use that to populate the graph,
# TODO: then read a log file to determine how well the correlation
# TODO: technique works.
