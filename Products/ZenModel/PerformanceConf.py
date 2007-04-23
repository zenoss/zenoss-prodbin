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
import glob
import zlib
import transaction
import logging
log = logging.getLogger("zen.PerformanceConf")

try:
    from base64 import urlsafe_b64encode
    raise ImportError
except ImportError, ex:
    def urlsafe_b64encode(s):
        import base64
        s = base64.encodestring(s)
        s = s.replace('+','-')
        s = s.replace('/','_')
        s = s.replace('\n','')
        return s

import xmlrpclib

from sets import Set

from ZODB.POSException import POSError
from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from Globals import InitializeClass

from Products.PythonScripts.standard import url_quote
from AccessControl import Permissions as permissions

from Products.ZenRelations.RelSchema import *

from Products.ZenUtils.Exceptions import ZentinelException
from Products.ZenUtils.Utils import basicAuthUrl

from Products.ZenEvents.ZenEventClasses import Status_Snmp

from Monitor import Monitor
from StatusColor import StatusColor

from ZenDate import ZenDate

PERF_ROOT = os.path.join(os.environ['ZENHOME'], "perf")

def performancePath(target):
    if target.startswith("/"): target = target[1:]
    return os.path.join(PERF_ROOT, target)

def manage_addPerformanceConf(context, id, title = None, REQUEST = None):
    """make a device class"""
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

    wmiCycleInterval = 60
    snmpCycleInterval = 300
    configCycleInterval = 30
    renderurl = ''
    renderuser = ''
    renderpass = ''
    defaultRRDCreateCommand = (
        'RRA:AVERAGE:0.5:1:2016',  # every 5 mins for 7 days
        'RRA:AVERAGE:0.5:4:2016',  # every 20 mins for 4 weeks
        'RRA:AVERAGE:0.5:24:1488', # every 2 hours for 4 months
        'RRA:AVERAGE:0.5:288:730', # every 1 day for 2 years 
        'RRA:MAX:0.5:4:2016',
        'RRA:MAX:0.5:24:1488',
        'RRA:MAX:0.5:288:730',
        )

    _properties = (
        {'id':'wmiCycleInterval','type':'int','mode':'w'},
        {'id':'snmpCycleInterval','type':'int','mode':'w'},
        {'id':'configCycleInterval','type':'int','mode':'w'},
        {'id':'renderurl','type':'string','mode':'w'},
        {'id':'renderuser','type':'string','mode':'w'},
        {'id':'renderpass','type':'string','mode':'w'},
        {'id':'defaultRRDCreateCommand','type':'lines','mode':'w'},
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
#                { 'id'            : 'edit'
#                , 'name'          : 'Edit'
#                , 'action'        : 'editPerformanceConf'
#                , 'permissions'   : ("Manage DMD",)
#                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (
                  permissions.view, )
                },
            )
          },
        )

    security.declareProtected('View','getDevices')
    def getDevices(self, devices=None):
        """Return information for snmp collection on all devices in the form
        (devname, ip, snmpport, snmpcommunity [(oid, path, type),])"""
        if devices:
            if not isinstance(devices, list):
                devices = Set([devices])
            else:
                devices = Set(devices)
        result = []
        for dev in self.devices():
            if devices and dev.id not in devices: continue
            dev = dev.primaryAq()
            if dev.snmpMonitorDevice():
                try:
                    result.append(dev.getSnmpOidTargets())
                except POSError: raise
                except:
                    log.exception("device %s", dev.id)
        return result

    def getDeviceUpdates(self, devices):
        """Return a list of devices that have changed.
        Takes a list of known devices and the time of last known change.
        The result is a list of devices that have changed,
        or not in the list."""
        lastChanged = dict(devices)
        new = Set()
        all = Set()
        for dev in self.devices():
            dev = dev.primaryAq()
            if dev.snmpMonitorDevice():
                all.add(dev.id)
                if lastChanged.get(dev.id, 0) < float(dev.getLastChange()):
                    new.add(dev.id)
        deleted = Set(lastChanged.keys()) - all
        return list(new | deleted)

    security.declareProtected('View','getDevices')
    def getSnmpStatus(self, devname=None):
        "Return the failure counts for Snmp" 
        result = []
        counts = {}
        try:
            # get all the events with /Status/Snmp
            zem = self.dmd.ZenEventManager
            conn = zem.connect()
            try:
                curs = conn.cursor()
                cmd = ('SELECT device, sum(count)  ' +
                       '  FROM status ' +
                       ' WHERE eventClass = "%s"' % Status_Snmp)
                if devname:
                    cmd += ' AND device = "%s"' % devname
                cmd += ' GROUP BY device'
                curs.execute(cmd);
                counts = dict([(d, int(c)) for d, c in curs.fetchall()])
            finally: zem.close(conn)
        except Exception, ex:
            log.exception('Unable to get Snmp Status')
            raise
        if devname:
            return [(devname, counts.get(devname, 0))]
        return [(dev.id, counts.get(dev.id, 0)) for dev in self.devices()]


    def getProcessStatus(self, device=None):
        "Get the known process status from the Event Manager"
        from Products.ZenEvents.ZenEventClasses import Status_OSProcess
        zem = self.dmd.ZenEventManager
        down = {}
        conn = zem.connect()
        try:
            curs = conn.cursor()
            query = ("SELECT device, component, count"
                    "  FROM status"
                    " WHERE eventClass = '%s'" % Status_OSProcess)
            if device:
                query += " AND device = '%s'" % device
            curs.execute(query)
            for device, component, count in curs.fetchall():
                down[device] = (component, count)
        finally: zem.close(conn)
        result = []
        for dev in self.devices():
            try:
                component, count = down[dev.id]
                result.append( (dev.id, component, count) )
            except KeyError:
                pass
        return result

    def getOSProcessConf(self, devices = None):
        '''Get the OS Process configuration for all devices.
        '''
        result = []
        for dev in self.devices():
            if devices and dev.id not in devices: continue
            dev = dev.primaryAq()
            if dev.snmpMonitorDevice():
                try:
                    procinfo = dev.getOSProcessConf()
                    if procinfo is None: continue
                    result.append(procinfo)
                except POSError: raise
                except:
                    log.exception("device %s", dev.id)
        return result


    def getDataSourceCommands(self, devices = None):
        '''Get the command configuration for all devices.
        '''
        result = []
        for dev in self.devices():
            if devices and dev.id not in devices: continue
            dev = dev.primaryAq()
            if dev.monitorDevice():
                try:
                    cmdinfo = dev.getDataSourceCommands()
                    if not cmdinfo: continue
                    result.append(cmdinfo)
                except POSError: raise
                except:
                    log.exception("device %s", dev.id)
        return result
        

    def getXmlRpcDevices(self, devname=None):
        '''Get the XMLRPC configuration for all devices.
        '''
        result = []
        for dev in self.devices():
            if devname and dev.id != devname: continue
            dev = dev.primaryAq()
            if dev.monitorDevice() and dev.getXmlRpcStatus() != -1:
                try:
                    result.append(dev.getXmlRpcTargets())
                except POSError: raise
                except:
                    log.exception("device %s", dev.id)
        return result


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
        

    def performanceGraphUrl(self, context, targetpath, targettype,
                            view, drange):
        """set the full path of the target and send to view"""
        targetpath = performancePath(targetpath[1:])
        gopts =  view.graphOpts(context, targetpath, targettype)
        ngopts = []
        width = 0
        for o in gopts: 
            if o.startswith('--width'): 
                width = o.split('=')[1].strip()
                continue
            ngopts.append(o)
        import base64
        gopts = urlsafe_b64encode(zlib.compress('|'.join(ngopts), 9))
        url = "%s/render?gopts=%s&drange=%d&width=%s" % (
                self.renderurl,gopts,drange, width)
        if self.renderurl.startswith("http"):
            return  "/zport/RenderServer/render" \
                    "?remoteUrl=%s&gopts=%s&drange=%d&width=%s" % (
                    url_quote(url),gopts,drange,width)
        else:
            return url

 
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
        if self.renderurl.startswith("http"):
            url = basicAuthUrl(self.renderuser, self.renderpass,
                                self.renderurl)
            server = xmlrpclib.Server(url)
        else:
            server = self.getObjByPath(self.renderurl)
        return server.summary(gopts)


    def currentValues(self, paths):
        "fill out full path and call to server"
        if self.renderurl.startswith("http"):
            url = basicAuthUrl(self.renderuser, self.renderpass,
                                self.renderurl)
            server = xmlrpclib.Server(url)
        else:
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
                remoteUrl = "%s/deleteRRDFiles?device=%s&datapoint=%s" % (self.renderurl,device,datapoint)
            else:
                remoteUrl = "%s/deleteRRDFiles?device=%s&datasource=%s" % (self.renderurl,device,datasource)
        rs = self.getDmd().getParentNode().RenderServer
        rs.deleteRRDFiles(device, datasource, datapoint, remoteUrl)

InitializeClass(PerformanceConf)
