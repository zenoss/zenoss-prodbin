#! /usr/bin/env python
# -*- coding: utf-8 -*-
# ##########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2006-2009 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
# ##########################################################################

__doc__ = """PerformanceConf
The configuration object for Performance servers
"""

import os
import zlib
import socket
import logging
log = logging.getLogger('zen.PerformanceConf')

try:
    from base64 import urlsafe_b64encode
    raise ImportError
except ImportError:


    def urlsafe_b64encode(s):
        """
        Encode a string so that it's okay to be used in an URL
        
        @param s: possibly unsafe string passed in by the user
        @type s: string
        @return: sanitized, url-safe version of the string
        @rtype: string
        """

        import base64
        s = base64.encodestring(s)
        s = s.replace('+', '-')
        s = s.replace('/', '_')
        s = s.replace('\n', '')
        return s


import xmlrpclib

from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions
from Globals import DTMLFile
from Globals import InitializeClass
from Monitor import Monitor
from Products.PythonScripts.standard import url_quote
from Products.Jobber.jobs import ShellCommandJob 
from Products.ZenModel.ZenossSecurity import *
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.Utils import basicAuthUrl, zenPath, binPath
from Products.ZenUtils.Utils import unused
from Products.ZenUtils.Utils import isXmlRpc
from Products.ZenUtils.Utils import setupLoggingHeader
from Products.ZenUtils.Utils import executeCommand
from Products.ZenUtils.Utils import clearWebLoggingStream
from Products.ZenModel.Device import manage_createDevice
from Products.ZenWidgets import messaging
from StatusColor import StatusColor

PERF_ROOT = None


def performancePath(target):
    """
    Return the base directory where RRD performance files are kept.
    
    @param target: path to performance file
    @type target: string
    @return: sanitized path to performance file
    @rtype: string
    """
    global PERF_ROOT
    if PERF_ROOT is None:
        PERF_ROOT = zenPath('perf')
    if target.startswith('/'):
        target = target[1:]
    return os.path.join(PERF_ROOT, target)


def manage_addPerformanceConf(context, id, title=None, REQUEST=None,):
    """
    Make a device class
    
    @param context: Where you are in the Zope acquisition path
    @type context: Zope context object
    @param id: unique identifier
    @type id: string
    @param title: user readable label (unused)
    @type title: string
    @param REQUEST: Zope REQUEST object
    @type REQUEST: Zope REQUEST object
    @return:
    @rtype:
    """
    unused(title)
    dc = PerformanceConf(id)
    context._setObject(id, dc)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                 + '/manage_main')


addPerformanceConf = DTMLFile('dtml/addPerformanceConf', globals())


class PerformanceConf(Monitor, StatusColor):
    """
    Configuration for Performance servers
    """
    portal_type = meta_type = 'PerformanceConf'

    monitorRootName = 'Performance'

    security = ClassSecurityInfo()
    security.setDefaultAccess('allow')

    eventlogCycleInterval = 60
    perfsnmpCycleInterval = 300
    processCycleInterval = 180
    statusCycleInterval = 60
    winCycleInterval = 60
    wmibatchSize = 10
    wmiqueryTimeout = 100
    configCycleInterval = 6 * 60

    zenProcessParallelJobs = 10

    pingTimeOut = 1.5
    pingTries = 2
    pingChunk = 75
    pingCycleInterval = 60
    maxPingFailures = 1440

    modelerCycleInterval = 720

    renderurl = '/zport/RenderServer'
    renderuser = ''
    renderpass = ''

    discoveryNetworks = ()

    # make the default rrdfile size smaller
    # we need the space to live within the disk cache
    defaultRRDCreateCommand = (
        'RRA:AVERAGE:0.5:1:600',   # every 5 mins for 2 days
        'RRA:AVERAGE:0.5:6:600',   # every 30 mins for 12 days
        'RRA:AVERAGE:0.5:24:600',  # every 2 hours for 50 days
        'RRA:AVERAGE:0.5:288:600', # every day for 600 days
        'RRA:MAX:0.5:6:600',
        'RRA:MAX:0.5:24:600',
        'RRA:MAX:0.5:288:600',
        )

    _properties = (
        {'id': 'eventlogCycleInterval', 'type': 'int', 'mode': 'w'},
        {'id': 'perfsnmpCycleInterval', 'type': 'int', 'mode': 'w'},
        {'id': 'processCycleInterval', 'type': 'int', 'mode': 'w'},
        {'id': 'statusCycleInterval', 'type': 'int', 'mode': 'w'},
        {'id': 'winCycleInterval', 'type': 'int', 'mode': 'w'},
        {'id': 'wmibatchSize', 'type': 'int', 'mode': 'w',
         'description':"Number of data objects to retrieve in a single WMI query",},
        {'id': 'wmiqueryTimeout', 'type': 'int', 'mode': 'w',
         'description':"Number of milliseconds to wait for WMI query to respond",},
        {'id': 'configCycleInterval', 'type': 'int', 'mode': 'w'},
        {'id': 'renderurl', 'type': 'string', 'mode': 'w'},
        {'id': 'renderuser', 'type': 'string', 'mode': 'w'},
        {'id': 'renderpass', 'type': 'string', 'mode': 'w'},
        {'id': 'defaultRRDCreateCommand', 'type': 'lines', 'mode': 'w'
         },
        {'id': 'zenProcessParallelJobs', 'type': 'int', 'mode': 'w'},
        {'id': 'pingTimeOut', 'type': 'float', 'mode': 'w'},
        {'id': 'pingTries', 'type': 'int', 'mode': 'w'},
        {'id': 'pingChunk', 'type': 'int', 'mode': 'w'},
        {'id': 'pingCycleInterval', 'type': 'int', 'mode': 'w'},
        {'id': 'maxPingFailures', 'type': 'int', 'mode': 'w'},
        {'id': 'modelerCycleInterval', 'type': 'int', 'mode': 'w'},
        {'id': 'discoveryNetworks', 'type': 'lines', 'mode': 'w'},
        )

    _relations = Monitor._relations + (
        ("devices", ToMany(ToOne,"Products.ZenModel.Device","perfServer")),
        )

    # Screen action bindings (and tab definitions)
    factory_type_information = (
        {   
            'immediate_view' : 'viewPerformanceConfOverview',
            'actions'        :
            (   
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewPerformanceConfOverview'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
                , 'action'        : 'editPerformanceConf'
                , 'permissions'   : ("Manage DMD",)
                },
                { 'id'            : 'performance'
                , 'name'          : 'Performance'
                , 'action'        : 'viewDaemonPerformance'
                , 'permissions'   : (permissions.view,)
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Modifications'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (ZEN_VIEW_MODIFICATIONS,)
                },
            )
          },
        )


    security.declareProtected('View', 'getDefaultRRDCreateCommand')
    def getDefaultRRDCreateCommand(self):
        """
        Get the default RRD Create Command, as a string.
        For example:
        '''RRA:AVERAGE:0.5:1:600
        RRA:AVERAGE:0.5:6:600
        RRA:AVERAGE:0.5:24:600
        RRA:AVERAGE:0.5:288:600
        RRA:MAX:0.5:288:600'''
        
        @return: RRD create command
        @rtype: string
        """
        return '\n'.join(self.defaultRRDCreateCommand)


    def findDevice(self, deviceName):
        """
        Return the object given the name
        
        @param deviceName: Name of a device
        @type deviceName: string
        @return: device corresponding to the name, or None
        @rtype: device object
        """
        brains = self.dmd.Devices._findDevice(deviceName)
        if brains:
            return brains[0].getObject()


    def getNetworkRoot(self):
        """
        Get the root of the Network object in the DMD
        
        @return: base DMD Network object
        @rtype: Network object
        """
        return self.dmd.Networks


    def buildGraphUrlFromCommands(self, gopts, drange):
        """
        Return an URL for the given graph options and date range
        
        @param gopts: graph options
        @type gopts: string
        @param drange: time range to use
        @type drange: string
        @return: URL to a graphic
        @rtype: string
        """
        newOpts = []
        width = 0
        for o in gopts:
            if o.startswith('--width'):
                width = o.split('=')[1].strip()
                continue
            newOpts.append(o)
        encodedOpts = urlsafe_b64encode(
                         zlib.compress('|'.join(newOpts), 9))
        url = '%s/render?gopts=%s&drange=%d&width=%s' % (
                 self.renderurl, encodedOpts, drange, width)
        if self.renderurl.startswith('proxy'):
            url = url.replace('proxy', 'http')
            return '/zport/RenderServer/render?remoteUrl=%s&gopts=%s&drange=%d&width=%s' % (
                 url_quote(url), encodedOpts, drange, width)
        else:
            return url


    def performanceGraphUrl(self, context, targetpath, targettype, view, drange):
        """
        Set the full path of the target and send to view
        
        @param context: Where you are in the Zope acquisition path
        @type context: Zope context object
        @param targetpath: device path of performance metric
        @type targetpath: string
        @param targettype: unused
        @type targettype: string
        @param view: view object
        @type view: Zope object
        @param drange: date range
        @type drange: string
        @return: URL to graph
        @rtype: string
        """
        unused(targettype)
        targetpath = performancePath(targetpath)
        gopts = view.getGraphCmds(context, targetpath)
        return self.buildGraphUrlFromCommands(gopts, drange)


    def performanceMGraphUrl(self, context, targetsmap, view, drange):
        """
        Set the full paths for all targts in map and send to view
        
        @param context: Where you are in the Zope acquisition path
        @type context: Zope context object
        @param targetsmap: list of (target, targettype) tuples
        @type targetsmap: list
        @param view: view object
        @type view: Zope object
        @param drange: date range
        @type drange: string
        @return: URL to graph
        @rtype: string
        """
        ntm = []
        for (target, targettype) in targetsmap:
            if target.find('.rrd') == -1:
                target += '.rrd'
            fulltarget = performancePath(target)
            ntm.append((fulltarget, targettype))
        gopts = view.multiGraphOpts(context, ntm)
        gopts = url_quote('|'.join(gopts))
        url = '%s/render?gopts=%s&drange=%d' % (self.renderurl, gopts, drange)
        if self.renderurl.startswith('http'):
            return '/zport/RenderServer/render?remoteUrl=%s&gopts=%s&drange=%d' % (
                 url_quote(url), gopts, drange)
        else:
            return url


    def renderCustomUrl(self, gopts, drange):
        """
        Return the URL for a list of custom gopts for a graph
        
        @param gopts: graph options
        @type gopts: string
        @param drange: date range
        @type drange: string
        @return: URL to graph
        @rtype: string
        """
        gopts = self._fullPerformancePath(gopts)
        gopts = url_quote('|'.join(gopts))
        url = '%s/render?gopts=%s&drange=%d' % (self.renderurl, gopts,
                drange)
        if self.renderurl.startswith('http'):
            return '/zport/RenderServer/render?remoteUrl=%s&gopts=%s&drange=%d'\
                 % (url_quote(url), gopts, drange)
        else:
            return url


    def performanceCustomSummary(self, gopts):
        """
        Fill out full path for custom gopts and call to server
        
        @param gopts: graph options
        @type gopts: string
        @return: URL
        @rtype: string
        """
        gopts = self._fullPerformancePath(gopts)
        renderurl = str(self.renderurl)
        if renderurl.startswith('proxy'):
            renderurl = self.renderurl.replace('proxy', 'http')
        if renderurl.startswith('http'):
            url = basicAuthUrl(str(self.renderuser),
                               str(self.renderpass), renderurl)
            server = xmlrpclib.Server(url)
        else:
            server = self.getObjByPath(renderurl)
        return server.summary(gopts)


    def fetchValues(self, paths, cf, resolution, start, end=""):
        """
        Return values
        
        @param paths: paths to performance metrics
        @type paths: list
        @param cf: RRD CF
        @type cf: string
        @param resolution: resolution
        @type resolution: string
        @param start: start time
        @type start: string
        @param end: end time
        @type end: string
        @return: values
        @rtype: list
        """
        url = self.renderurl
        if url.startswith("http"):
            url = basicAuthUrl(self.renderuser, self.renderpass, self.renderurl)
            server = xmlrpclib.Server(url, allow_none=True)
        else:
            if not self.renderurl:
                raise KeyError
            server = self.getObjByPath(self.renderurl)
        return server.fetchValues(map(performancePath, paths), cf,
                                  resolution, start, end)


    def currentValues(self, paths):
        """
        Fill out full path and call to server
        
        @param paths: paths to performance metrics
        @type paths: list
        @return: values
        @rtype: list
        """
        url = self.renderurl
        if url.startswith('proxy'):
            url = self.renderurl.replace('proxy', 'http')
        if url.startswith('http'):
            url = basicAuthUrl(self.renderuser, self.renderpass,
                               self.renderurl)
            server = xmlrpclib.Server(url)
        else:
            if not self.renderurl:
                raise KeyError
            server = self.getObjByPath(self.renderurl)
        return server.currentValues(map(performancePath, paths))


    def _fullPerformancePath(self, gopts):
        """
        Add full path to a list of custom graph options
        
        @param gopts: graph options
        @type gopts: string
        @return: full path + graph options
        @rtype: string
        """
        for i in range(len(gopts)):
            opt = gopts[i]
            if opt.find('DEF') == 0:
                opt = opt.split(':')
                (var, file) = opt[1].split('=')
                file = performancePath(file)
                opt[1] = '%s=%s' % (var, file)
                opt = ':'.join(opt)
                gopts[i] = opt
        return gopts


    security.declareProtected('View', 'performanceDeviceList')
    def performanceDeviceList(self, force=True):
        """
        Return a list of URLs that point to our managed devices
        
        @param force: unused
        @type force: boolean
        @return: list of device objects
        @rtype: list
        """
        unused(force)
        devlist = []
        for dev in self.devices():
            dev = dev.primaryAq()
            if not dev.pastSnmpMaxFailures() and dev.monitorDevice():
                devlist.append(dev.getPrimaryUrlPath(full=True))
        return devlist


    security.declareProtected('View', 'performanceDataSources')
    def performanceDataSources(self):
        """
        Return a string that has all the definitions for the performance DS's.
        
        @return: list of Data Sources
        @rtype: string
        """
        dses = []
        oidtmpl = 'OID %s %s'
        dstmpl = """datasource %s
        rrd-ds-type = %s
        ds-source = snmp://%%snmp%%/%s%s
        """
        rrdconfig = self.getDmdRoot('Devices').rrdconfig
        for ds in rrdconfig.objectValues(spec='RRDDataSource'):
            if ds.isrow:
                inst = '.%inst%'
            else:
                inst = ''
            dses.append(oidtmpl % (ds.getName(), ds.oid))
            dses.append(dstmpl % (ds.getName(), ds.rrdtype,
                        ds.getName(), inst))
        return '\n'.join(dses)

    def deleteRRDFiles(self, device, datasource=None, datapoint=None):
        """
        Remove RRD performance data files
        
        @param device: Name of a device or entry in DMD
        @type device: string
        @param datasource: datasource name
        @type datasource: string
        @param datapoint: datapoint name
        @type datapoint: string
        """
        remoteUrl = None
        if self.renderurl.startswith('http'):
            if datapoint:
                remoteUrl = '%s/deleteRRDFiles?device=%s&datapoint=%s' % (
                     self.renderurl, device, datapoint)
            elif datasource:
                remoteUrl = '%s/deleteRRDFiles?device=%s&datasource=%s' % (
                     self.renderurl, device, datasource)
            else:
                remoteUrl = '%s/deleteRRDFiles?device=%s' % (
                     self.renderurl, device)
        rs = self.getDmd().getParentNode().RenderServer
        rs.deleteRRDFiles(device, datasource, datapoint, remoteUrl)


    def setPerformanceMonitor(self, performanceMonitor=None, deviceNames=None, REQUEST=None):
        """
        Provide a method to set performance monitor from any organizer
        
        @param performanceMonitor: DMD object that collects from a device
        @type performanceMonitor: DMD object
        @param deviceNames: list of device names
        @type deviceNames: list
        @param REQUEST: Zope REQUEST object
        @type REQUEST: Zope REQUEST object
        """
        if not performanceMonitor:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser('Error',
                        'No monitor was selected.',
                        priority=messaging.WARNING)
            return self.callZenScreen(REQUEST)
        if deviceNames is None:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser('Error',
                        'No devices were selected.',
                        priority=messaging.WARNING)
            return self.callZenScreen(REQUEST)
        for devName in deviceNames:
            dev = self.devices._getOb(devName)
            dev = dev.primaryAq()
            dev.setPerformanceMonitor(performanceMonitor)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser('Monitor Set',
                    'Performance monitor was set to %s.'
                     % performanceMonitor)
            if REQUEST.has_key('oneKeyValueSoInstanceIsntEmptyAndEvalToFalse'):
                return REQUEST['message']
            else:
                return self.callZenScreen(REQUEST)


    security.declareProtected('View', 'getPingDevices')
    def getPingDevices(self):
        """
        Return devices associated with this monitor configuration.
        
        @return: list of devices for this monitor
        @rtype: list
        """
        devices = []
        for dev in self.devices.objectValuesAll():
            dev = dev.primaryAq()
            if dev.monitorDevice() and not dev.zPingMonitorIgnore:
                devices.append(dev)
        return devices

    def _executeZenDiscCommand(self, deviceName, devicePath= "/Discovered", 
                      performanceMonitor="localhost", discoverProto="snmp",
                      zSnmpPort=161, zSnmpCommunity="", background=False,
                      REQUEST=None):
        """
        Execute zendisc on the new device and return result
        
        @param deviceName: Name of a device
        @type deviceName: string
        @param devicePath: DMD path to create the new device in
        @type devicePath: string
        @param performanceMonitor: DMD object that collects from a device
        @type performanceMonitor: DMD object
        @param discoverProto: auto or none
        @type discoverProto: string
        @param zSnmpPort: zSnmpPort
        @type zSnmpPort: string
        @param zSnmpCommunity: SNMP community string
        @type zSnmpCommunity: string
        @param REQUEST: Zope REQUEST object
        @type REQUEST: Zope REQUEST object
        @return:
        @rtype:
        """
        zm = binPath('zendisc')
        zendiscCmd = [zm]
        zendiscOptions = ['run', '--now','-d', deviceName,
                     '--monitor', performanceMonitor, 
                     '--deviceclass', devicePath]
        if REQUEST: 
            zendiscOptions.append("--weblog")
        zendiscCmd.extend(zendiscOptions)
        if background:
            log.info('queued job: %s', " ".join(zendiscCmd))
            result = self.dmd.JobManager.addJob(ShellCommandJob,
                                                    zendiscCmd) 
        else:
            result = executeCommand(zendiscCmd, REQUEST)
        return result

    def executeCollectorCommand(self, command, args, REQUEST=None):
        """
        Executes the collector based daemon command.
        
        @param command: the collector daemon to run, should not include path
        @type command: string
        @param args: list of arguments for the command
        @type args: list of strings
        @param REQUEST: Zope REQUEST object
        @type REQUEST: Zope REQUEST object
        @return: result of the command
        @rtype: string
        """
        cmd = binPath(command)
        daemonCmd = [cmd]
        daemonCmd.extend(args)
        result = executeCommand(daemonCmd, REQUEST)
        return result


    def collectDevice(self, device=None, setlog=True, REQUEST=None,
        generateEvents=False, background=False):
        """
        Collect the configuration of this device AKA Model Device

        @permission: ZEN_MANAGE_DEVICE
        @param device: Name of a device or entry in DMD
        @type device: string
        @param setlog: If true, set up the output log of this process
        @type setlog: boolean
        @param REQUEST: Zope REQUEST object
        @type REQUEST: Zope REQUEST object
        @param generateEvents: unused
        @type generateEvents: string
        """
        xmlrpc = isXmlRpc(REQUEST)
        if setlog and REQUEST and not xmlrpc:
            handler = setupLoggingHeader(device, REQUEST)

        zenmodelerOpts = ['run', '--now', '--monitor', self.id, 
                            '-F', '-d', device.id]
        if REQUEST:
            zenmodelerOpts.append('--weblog')
        result = self._executeZenModelerCommand(zenmodelerOpts, 
                                                background, REQUEST)
        if result and xmlrpc:
            return result
        log.info('configuration collected')

        if setlog and REQUEST and not xmlrpc:
            clearWebLoggingStream(handler)

        if xmlrpc:
            return 0


    def _executeZenModelerCommand(self, zenmodelerOpts, 
                                    background=False, REQUEST=None):
        """
        Execute zenmodeler and return result
        
        @param zenmodelerOpts: zenmodeler command-line options
        @type zenmodelerOpts: string
        @param REQUEST: Zope REQUEST object
        @type REQUEST: Zope REQUEST object
        @return: results of command
        @rtype: string
        """
        zm = binPath('zenmodeler')
        zenmodelerCmd = [zm]
        zenmodelerCmd.extend(zenmodelerOpts)
        if background:
            log.info('queued job: %s', " ".join(zenmodelerCmd))
            result = self.dmd.JobManager.addJob(ShellCommandJob,zenmodelerCmd) 
        else:
            result = executeCommand(zenmodelerCmd, REQUEST)
        return result


InitializeClass(PerformanceConf)
