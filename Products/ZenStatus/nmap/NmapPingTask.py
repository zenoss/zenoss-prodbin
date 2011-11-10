###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """NmapPingTask

Pings a all devices in the current device list.
"""

import logging
log = logging.getLogger("zen.NmapPingTask")
import tempfile
from twisted.internet import utils
from twisted.internet import defer
import os.path
from cStringIO import StringIO

import Globals
from zope import interface
from zope import component
from Products import ZenCollector
from Products.ZenCollector.tasks import BaseTask, TaskStates
from Products.ZenCollector import interfaces
from Products.ZenCollector.tasks import SimpleTaskFactory
from Products.ZenUtils.Utils import zenPath

# imports from within ZenStatus
from Products.ZenStatus import PingTask
from PingResult import PingResult, parseNmapXmlToDict
from Products.ZenStatus.PingCollectionPreferences import PingCollectionPreferences
from Products.ZenStatus.interfaces import IPingTaskFactory

class NmapPingCollectionPreferences(PingCollectionPreferences):
    
    def postStartup(self):
        """
        Hook in to application startup and start background NmapPingTask.
        """
        daemon = component.getUtility(interfaces.ICollector)
        task = NmapPingTask (
            'NmapPingTask',
            'NmapPingTask',
            taskConfig=daemon._prefs
        )
        daemon._scheduler.addTask(task, now=True)

class NPingTaskFactory(object):
    """
    A Factory to create PingTasks that do not run. This allows NmapPingTask
    to use the created PingTasks as placeholders for configuration.
    """
    interface.implements(IPingTaskFactory)

    def __init__(self):
        self.reset()

    def build(self):
        task = PingTask(
            self.name,
            self.configId,
            self.interval,
            self.config,
        )
        # schedule so far in to the future it never runs
        task.interval = 10000000
        return task

    def reset(self):
        self.name = None
        self.configId = None
        self.interval = None
        self.config = None    

class NmapPingTask(BaseTask):
    interface.implements(ZenCollector.interfaces.IScheduledTask)
    """
    NmapPingTask pings all PingTasks using using nmap.
    """

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
        super(NmapPingTask, self).__init__(
                 taskName, configId,
                 scheduleIntervalSeconds, taskConfig=None
              )

        # Needed for interface
        self.name = taskName
        self.configId = configId
        self.state = TaskStates.STATE_IDLE
        self.interval = scheduleIntervalSeconds

        if taskConfig is None:
            raise TypeError("taskConfig cannot be None")
        self._preferences = taskConfig

        self._daemon = component.getUtility(ZenCollector.interfaces.ICollector)
        self._dataService = component.queryUtility(ZenCollector.interfaces.IDataService)
        self._eventService = component.queryUtility(ZenCollector.interfaces.IEventService)
        self._nmapBinary = zenPath("bin/nmap")
        
    def _getNmapCmd(self, inputFile, outputType="xml"):
        """
        Return a list of command line args to nmap based on configured settings.
        """
        args = []
        args.extend(["-iL", inputFile])  # input file
        args.append("-sn")               # don't port scan the hosts
        args.append("-PE")               # use ICMP echo 
        args.append("-n")                # don't resolve hosts internally 
        args.append("--traceroute")      # perform a traceroute along with ping
        args.append("--privileged")      # assume we can open raw socket
        if outputType == 'xml':
            args.extend(["-oX", '-']) # outputXML to stdout
        else:
            raise ValueError("Unsupported nmap output type: %s" % outputType)
        return args

    def doTask(self):
        """
        BatchPingDevices !
        """
        log.debug('---- BatchPingDevices ----')
        return self._batchPing()
        
    def _getPingTasks(self):
        """
        Iterate the daemons task list and find PingTask tasks
        """
        tasks = self._daemon._scheduler._tasks
        pingTasks = {}
        for configName, task in tasks.iteritems():
            if isinstance(task.task, PingTask):
                pingTasks[configName] = task.task
        return pingTasks

    @defer.inlineCallbacks
    def _batchPing(self):    
        # find all devices to Ping
        ipTasks = self._getPingTasks()
        if len(ipTasks) == 0:
            log.info("No ips to ping!")
            raise StopIteration() # exit this generator

        with tempfile.NamedTemporaryFile(prefix='zenping_nmap_') as tfile:
            for taskName, task in ipTasks.iteritems():
                tfile.write("%s\n" % task.config.ip)
            tfile.flush()

            log.debug("wrote temp file %s with input to nmap", tfile.name)
            out, err, exitCode = yield utils.getProcessOutputAndValue(self._nmapBinary, self._getNmapCmd(tfile.name))
            log.debug("got %d back from nmap", exitCode)
            if exitCode != 0:
                tfile.seek(0)
                log.debug("input file: %s:%s", out, err)
                log.debug("output file: %s", out)
                raise Exception("Problem running nmap!")
            log.debug("parsing nmap results")
            results = parseNmapXmlToDict(StringIO(out))

            # update the states of all the PingTasks without giving time to the reactor!
            # Correlation should be based on the state of the entire result of the ping job.
            downTasks = {}
            for taskName, ipTask in ipTasks.iteritems():
                ip = ipTask.config.ip
                if ip in results:
                    result = results[ip]
                    log.debug("%s is %s", result.address, result.getStatusString())
                    ipTask.logPingResult(result)
                    if result.isUp:
                        ipTask.sendPingUp()
                    else:
                        # defer sending down events to correlate ping downs
                        downTasks[ip] = ipTask
                else:
                    # defer sending down events to correlate ping downs
                    downTasks[ip] = ipTask

            # correlation can be interwoven
            for currentIp, ipTask in downTasks.iteritems():
                # walk the hops in the traceroute
                for hop in ipTask.trace:
                    # if a hop.ip alog the traceroute is in our list of down ips
                    # and that hop.ip is not the currentIp then
                    if hop.ip in downTasks and hop.ip != currentIp:
                        # we found our root cause!
                        rootCause = downTasks[hop.ip]
                        yield ipTask.sendPingDown(rootCause=rootCause)
                        break
                else:
                    # no root cause found
                    yield ipTask.sendPingDown()

            # TODO: we could go a step further and ping all the ips along the last good
            # traceroute to give some insight as to where the problem may lie

    def displayStatistics(self):
        """
        Called by the collector framework scheduler, and allows us to
        see how each task is doing.
        """
        pass

