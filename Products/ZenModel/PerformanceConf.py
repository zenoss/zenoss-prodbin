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

__doc__="""PerformanceConf

The configuration object for Performance servers


$Id: PerformanceConf.py,v 1.30 2004/04/06 18:16:30 edahl Exp $"""

__version__ = "$Revision: 1.30 $"[11:-2]

import os
import zlib
import logging
log = logging.getLogger("zen.PerformanceConf")

try:
    from base64 import urlsafe_b64encode
    raise ImportError
except ImportError:
    def urlsafe_b64encode(s):
        import base64
        s = base64.encodestring(s)
        s = s.replace('+','-')
        s = s.replace('/','_')
        s = s.replace('\n','')
        return s
import xmlrpclib

from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from Globals import InitializeClass

from Products.PythonScripts.standard import url_quote
from AccessControl import Permissions as permissions

from Products.ZenRelations.RelSchema import *

from Products.ZenUtils.Utils import basicAuthUrl, zenPath

from Monitor import Monitor
from StatusColor import StatusColor
from Products.ZenUtils.Utils import unused

PERF_ROOT=None

def performancePath(target):
    global PERF_ROOT
    if PERF_ROOT is None:
        PERF_ROOT = zenPath("perf")
    if target.startswith("/"): target = target[1:]
    return os.path.join(PERF_ROOT, target)

def manage_addPerformanceConf(context, id, title = None, REQUEST = None):
    """make a device class"""
    unused(title)
    dc = PerformanceConf(id)
    context._setObject(id, dc)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addPerformanceConf = DTMLFile('dtml/addPerformanceConf',globals())

class PerformanceConf(Monitor, StatusColor):
    '''Configuration for Performance servers'''
    portal_type = meta_type = "PerformanceConf"
    
    monitorRootName = "Performance"

    security = ClassSecurityInfo()
    security.setDefaultAccess('allow')

    eventlogCycleInterval = 60
    perfsnmpCycleInterval = 300
    processCycleInterval = 180
    statusCycleInterval = 60
    winCycleInterval = 60
    winmodelerCycleInterval = 60
    
    configCycleInterval = 6*60

    zenProcessParallelJobs = 10

    pingTimeOut = 1.5
    pingTries = 2
    pingChunk = 75
    pingCycleInterval = 60
    maxPingFailures = 1440

    modelerCycleInterval = 720 * 60

    renderurl = '/zport/RenderServer'
    renderuser = ''
    renderpass = ''

    # make the default rrdfile size smaller
    # we need the space to live within the disk cache
    defaultRRDCreateCommand = (
        'RRA:AVERAGE:0.5:1:600',    # every 5 mins for 2 days
        'RRA:AVERAGE:0.5:6:600',    # every 30 mins for 12 days
        'RRA:AVERAGE:0.5:24:600',   # every 2 hours for 50 days
        'RRA:AVERAGE:0.5:288:600',  # every day for 600 days
        'RRA:MAX:0.5:6:600',
        'RRA:MAX:0.5:24:600',
        'RRA:MAX:0.5:288:600',
        )

    _properties = (
        {'id':'eventlogCycleInterval','type':'int','mode':'w'},
        {'id':'perfsnmpCycleInterval','type':'int','mode':'w'},
        {'id':'processCycleInterval','type':'int','mode':'w'},
        {'id':'statusCycleInterval','type':'int','mode':'w'},
        {'id':'winCycleInterval','type':'int','mode':'w'},
        {'id':'winmodelerCycleInterval','type':'int','mode':'w'},
        {'id':'configCycleInterval','type':'int','mode':'w'},
        {'id':'renderurl','type':'string','mode':'w'},
        {'id':'renderuser','type':'string','mode':'w'},
        {'id':'renderpass','type':'string','mode':'w'},
        {'id':'defaultRRDCreateCommand','type':'lines','mode':'w'},
        {'id':'zenProcessParallelJobs','type':'int','mode':'w'},
        {'id':'pingTimeOut','type':'float','mode':'w'},
        {'id':'pingTries','type':'int','mode':'w'},
        {'id':'pingChunk','type':'int','mode':'w'},
        {'id':'pingCycleInterval','type':'int','mode':'w'},
        {'id':'maxPingFailures','type':'int','mode':'w'},
        {'id':'modelerCycleInterval','type':'int','mode':'w'},
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
                , 'permissions'   : (
                  permissions.view, )
                },
            )
          },
        )

    security.declareProtected('View','getDefaultRRDCreateCommand')
    def getDefaultRRDCreateCommand(self):
        """Get the default RRD Create Command, as a string.
        For example:
                 '''RRA:AVERAGE:0.5:1:600
                    RRA:AVERAGE:0.5:6:600
                    RRA:AVERAGE:0.5:24:600
                    RRA:AVERAGE:0.5:288:600
                    RRA:MAX:0.5:288:600'''
        """
        return "\n".join(self.defaultRRDCreateCommand)


    def buildGraphUrlFromCommands(self, gopts, drange):
        ''' Return a url for the given graph options and date range
        '''
        newOpts = []
        width = 0
        for o in gopts: 
            if o.startswith('--width'): 
                width = o.split('=')[1].strip()
                continue
            newOpts.append(o)
        encodedOpts = urlsafe_b64encode(zlib.compress('|'.join(newOpts), 9))
        url = "%s/render?gopts=%s&drange=%d&width=%s" % (
                self.renderurl, encodedOpts, drange, width)
        if self.renderurl.startswith("proxy"):
            url = url.replace("proxy", "http")
            return  "/zport/RenderServer/render" \
                    "?remoteUrl=%s&gopts=%s&drange=%d&width=%s" % (
                    url_quote(url), encodedOpts, drange, width)
        else:
            return url
        
        
    def performanceGraphUrl(self, context, targetpath, targettype,
                            view, drange):
        """set the full path of the target and send to view"""
        unused(targettype)
        targetpath = performancePath(targetpath)
        gopts =  view.getGraphCmds(context, targetpath)
        return self.buildGraphUrlFromCommands(gopts, drange)
 
 
    def performanceMGraphUrl(self, context, targetsmap, view, drange):
        """set the full paths for all targts in map and send to view"""
        ntm = []
        for target, targettype in targetsmap:
            if target.find('.rrd') == -1: target += '.rrd'
            fulltarget = performancePath(target)
            ntm.append((fulltarget, targettype))
        gopts =  view.multiGraphOpts(context, ntm)
        gopts = url_quote('|'.join(gopts))
        url = "%s/render?gopts=%s&drange=%d" % (self.renderurl,gopts,drange)
        if self.renderurl.startswith("http"):
            return "/zport/RenderServer/render?remoteUrl=%s&gopts=%s&drange=%d" % (url_quote(url),gopts,drange)
        else:
            return url

    def renderCustomUrl(self, gopts, drange):
        "return the for a list of custom gopts for a graph"
        gopts = self._fullPerformancePath(gopts)
        gopts = url_quote('|'.join(gopts))
        url = "%s/render?gopts=%s&drange=%d" % (self.renderurl,gopts,drange)
        if self.renderurl.startswith("http"):
            return "/zport/RenderServer/render?remoteUrl=%s&gopts=%s&drange=%d" % (url_quote(url),gopts,drange)
        else:
            return url

    def performanceCustomSummary(self, gopts):
        "fill out full path for custom gopts and call to server"
        gopts = self._fullPerformancePath(gopts)
        renderurl = str(self.renderurl)
        if renderurl.startswith('proxy'):
            renderurl = self.renderurl.replace('proxy','http')
        if renderurl.startswith("http"):
            url = basicAuthUrl(str(self.renderuser), 
                               str(self.renderpass), 
                               renderurl)
            server = xmlrpclib.Server(url)
        else:
            server = self.getObjByPath(renderurl)
        return server.summary(gopts)


    def currentValues(self, paths):
        "fill out full path and call to server"
        url = self.renderurl
        if url.startswith('proxy'):
            url = self.renderurl.replace('proxy','http')
        if url.startswith("http"):
            url = basicAuthUrl(self.renderuser, self.renderpass, self.renderurl)
            server = xmlrpclib.Server(url)
        else:
            if not self.renderurl: raise KeyError
            server = self.getObjByPath(self.renderurl)
        return server.currentValues(map(performancePath, paths))


    def _fullPerformancePath(self, gopts):
        "add full path to a list of custom graph options"
        for i in range(len(gopts)):
            opt = gopts[i]
            if opt.find("DEF") == 0:
                opt = opt.split(':')
                var, file = opt[1].split('=')
                file = performancePath(file)
                opt[1] = "%s=%s" % (var, file)
                opt = ':'.join(opt)
                gopts[i] = opt
        return gopts
   

    security.declareProtected('View','performanceDeviceList')
    def performanceDeviceList(self, force=True):
        """Return a list of urls that point to our managed devices"""
        unused(force)
        devlist = []
        for dev in self.devices():
            dev = dev.primaryAq()
            if not dev.pastSnmpMaxFailures() and dev.monitorDevice():
                devlist.append(dev.getPrimaryUrlPath(full=True))
        return devlist
       

    security.declareProtected('View','performanceDataSources')
    def performanceDataSources(self):
        """Return a string that has all the definitions for the performance ds's.
        """
        dses = []
        oidtmpl = "OID %s %s"
        dstmpl = """datasource %s
        rrd-ds-type = %s
        ds-source = snmp://%%snmp%%/%s%s
        """
        rrdconfig = self.getDmdRoot("Devices").rrdconfig
        for ds in rrdconfig.objectValues(spec="RRDDataSource"):
            if ds.isrow:
                inst = ".%inst%"
            else:
                inst = ''
            dses.append(oidtmpl % (ds.getName(), ds.oid))
            dses.append(dstmpl %(ds.getName(), ds.rrdtype, ds.getName(), inst))
        return "\n".join(dses)     

    def deleteRRDFiles(self, device, datasource=None, datapoint=None):
        remoteUrl = None
        if self.renderurl.startswith("http"):
            if datapoint:
                remoteUrl = "%s/deleteRRDFiles?device=%s&datapoint=%s" % (
                                self.renderurl,device,datapoint)
            elif datasource:
                remoteUrl = "%s/deleteRRDFiles?device=%s&datasource=%s" % (
                                self.renderurl,device,datasource)
            else:
                remoteUrl = "%s/deleteRRDFiles?device=%s" % (self.renderurl,device)
        rs = self.getDmd().getParentNode().RenderServer
        rs.deleteRRDFiles(device, datasource, datapoint, remoteUrl)

    def setPerformanceMonitor(self,
                              performanceMonitor=None,
                              deviceNames=None, 
                              REQUEST=None):
        """ Provide a method to set performance monitor from any organizer """
        if not performanceMonitor:
            if REQUEST: REQUEST['message'] = "No Monitor Selected"
            return self.callZenScreen(REQUEST)
        if deviceNames is None:
            if REQUEST: REQUEST['message'] = "No Devices Selected"
            return self.callZenScreen(REQUEST)
        for devName in deviceNames:
            dev = self.devices._getOb(devName)
            dev = dev.primaryAq()
            dev.setPerformanceMonitor(performanceMonitor)
        if REQUEST: 
            REQUEST['message'] = "Performance monitor set to %s" % (
                                    performanceMonitor)
            if REQUEST.has_key('oneKeyValueSoInstanceIsntEmptyAndEvalToFalse'):
                return REQUEST['message']
            else:
                return self.callZenScreen(REQUEST)


    security.declareProtected('View','getPingDevices')
    def getPingDevices(self):
        '''Return devices associated with this monitor configuration.
        '''
        devices = []
        for dev in self.devices.objectValuesAll():
            dev = dev.primaryAq()
            if dev.monitorDevice() and not dev.zPingMonitorIgnore: 
                devices.append(dev)
        return devices


InitializeClass(PerformanceConf)
