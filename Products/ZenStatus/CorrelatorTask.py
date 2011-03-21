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
                                             ICollector,\
                                             IEventService,\
                                             IScheduledTask
from Products.ZenCollector.tasks import BaseTask,\
                                        TaskStates

from Products.ZenEvents.ZenEventClasses import Status_Ping

STATUS_EVENT = { 
                'eventClass' : Status_Ping,
                'component' : 'zenping',
                'eventGroup' : 'Ping' }

# Event 'suppressed' state
SUPPRESSED = 2

class TopologyCorrelatorTask(BaseTask):
    zope.interface.implements(IScheduledTask)

    def __init__(self,
                 taskName, configId,
                 scheduleIntervalSeconds=60,
                 taskConfig=None):
        """
        @param deviceId: the Zenoss deviceId to watch
        @type deviceId: string
        @param taskName: the unique identifier for this task
        @type taskName: string
        @param scheduleIntervalSeconds: the interval at which this task will be
               collected
        @type scheduleIntervalSeconds: int
        @param taskConfig: the configuration for this task
        """
        super(TopologyCorrelatorTask, self).__init__()

        # Needed for interface
        self.name = taskName
        self.configId = configId
        self.state = TaskStates.STATE_IDLE
        self.interval = scheduleIntervalSeconds

        # This needs to run after other processes have stopped
        self.stopPhase = 'before'
        self.stopOrder = 10

        if taskConfig is None:
            raise TypeError("taskConfig cannot be None")
        self._preferences = taskConfig

        self._daemon = zope.component.getUtility(ICollector)
        if taskName.endswith('IPv6'):
            self.version = 6
            self._network = self._daemon.ipv6network
        else:
            self.version = 4
            self._network = self._daemon.network

        self._topology = self._network.topology
        self._downDevices = self._network.downDevices
        self._notModeled = self._network.notModeled

        self._dataService = zope.component.queryUtility(IDataService)
        self._eventService = zope.component.queryUtility(IEventService)

        self._lastErrorMsg = ''

    def doTask(self):
        """
        Determine root cause for IPs being down and send events.
        """
        log.debug('---- IPv%d correlation begins ----', self.version)
        # Prune out intermediate devices that we don't ping
        pingGraph = self._network.subgraphPingNodes()

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

        stats = 'IPv%d correlator sent %d root cause and %d victim events' % (
                self.version, rootEvents, victimEvents)
        log.debug(stats)
        log.debug('---- IPv%d correlation ends ----', self.version)
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
            self.sendPingEvent(task.pingjob, root=root,
                               eventState=SUPPRESSED)

    def sendPingEvent(self, pj, root, eventState=None):
        """
        Send an event based on a ping job to the event backend.
        """
        message = pj.message
        if not message:
            if pj.severity == 0:
                message = "Device %s is UP!" % pj.hostname
            else:
                message = "Device %s is DOWN!" % pj.hostname
        evt = dict(device=pj.hostname,
                   ipAddress=pj.ipaddr,
                   summary=message,
                   severity=pj.severity,
                   eventClass=Status_Ping,
                   eventGroup='Ping',
                   rootDevice=root,
                   component=pj.iface)
        if eventState is not None:
            evt['eventState'] = eventState
        self._eventService.sendEvent(evt)

    def displayStatistics(self):
        """
        Called by the collector framework scheduler, and allows us to
        see how each task is doing.
        """
        nodes = self._network.topology.number_of_nodes()
        edges = self._network.topology.number_of_edges()
        down = len(self._network.downDevices)
        display = "%s nodes: %d edges: %d down: %d\n" % (
            self.name, nodes, edges, down)

        if self._lastErrorMsg:
            display += "%s\n" % self._lastErrorMsg
        return display

    def cleanup(self):
        # Do one last round of correlation before exiting zenping
        return self.doTask()


#if __name__=='__main__':
# TODO: Debugging tool
# TODO: read a topology file and use that to populate the graph,
# TODO: then read a log file to determine how well the correlation
# TODO: technique works.
