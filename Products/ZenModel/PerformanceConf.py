#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""PerformanceConf

The configuration object for Performance servers


$Id: PerformanceConf.py,v 1.30 2004/04/06 18:16:30 edahl Exp $"""

__version__ = "$Revision: 1.30 $"[11:-2]

import os
import glob
import transaction
import logging
log = logging.getLogger("zen.PerformanceConf")

import xmlrpclib

from ZODB.POSException import POSError
from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from Globals import InitializeClass

from Products.PythonScripts.standard import url_quote
from AccessControl import Permissions as permissions

from Products.ZenRelations.RelSchema import *

from Products.ZenUtils.Exceptions import ZentinelException
from Products.ZenUtils.Utils import basicAuthUrl

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
        {'id':'snmpCycleInterval','type':'int','mode':'w'},
        {'id':'configCycleInterval','type':'int','mode':'w'},
        {'id':'renderurl','type':'string','mode':'w'},
        {'id':'renderuser','type':'string','mode':'w'},
        {'id':'renderpass','type':'string','mode':'w'},
        {'id':'defaultRRDCreateCommand','type':'lines','mode':'w'},
        )
    _relations = Monitor._relations + (
        ("devices", ToMany(ToOne,"Device","perfServer")),
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
    def getDevices(self, devname=None):
        """Return information for snmp collection on all devices in the form
        (devname, ip, snmpport, snmpcommunity [(oid, path, type),])"""
        result = []
        for dev in self.devices():
            if devname and dev.id != devname: continue
            dev = dev.primaryAq()
            if dev.monitorDevice() and dev.getSnmpStatus() != -1:
                try:
                    result.append(dev.getSnmpOidTargets())
                except POSError: raise
                except:
                    log.exception("device %s", dev.id)
        return result


    def getOSProcessConf(self, devname=None):
        '''Get the OS Process configuration for all devices.
        '''
        result = []
        for dev in self.devices():
            if devname and dev.id != devname: continue
            dev = dev.primaryAq()
            if dev.monitorDevice() and dev.getSnmpStatus() != -1:
                try:
                    procinfo = dev.getOSProcessConf()
                    if procinfo is None: continue
                    result.append(procinfo)
                except POSError: raise
                except:
                    log.exception("device %s", dev.id)
        return result


    def getDataSourceCommands(self, devname=None):
        '''Get the command configuration for all devices.
        '''
        result = []
        for dev in self.devices():
            if devname and dev.id != devname: continue
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
        gopts = url_quote('|'.join(gopts))
        return "%s/render?gopts=%s&drange=%d" % (self.renderurl,gopts,drange)

 
    def performanceMGraphUrl(self, context, targetsmap, view, drange):
        """set the full paths for all targts in map and send to view"""
        ntm = []
        for target, targettype in targetsmap:
            if target.find('.rrd') == -1: target += '.rrd'
            fulltarget = performancePath(target)
            ntm.append((fulltarget, targettype))
        gopts =  view.multiGraphOpts(context, ntm)
        gopts = url_quote('|'.join(gopts))
        return "%s/render?gopts=%s&drange=%d" % (self.renderurl,gopts,drange)


    def renderCustomUrl(self, gopts, drange):
        "return the for a list of custom gopts for a graph"
        gopts = self._fullPerformancePath(gopts)
        gopts = url_quote('|'.join(gopts))
        return "%s/render?gopts=%s&drange=%d" % (self.renderurl,gopts,drange)


    def performanceCustomSummary(self, gopts):
        "fill out full path for custom gopts and call to server"
        gopts = self._fullPerformancePath(gopts)
        if self.renderurl.startswith("http"):
            url = basicAuthUrl(self.renderuser, self.renderpass,
                                self.renderurl)
            server = xmlrpclib.Server(url)
        else:
            server = self.unrestrictedTraverse(self.renderurl)
        return server.summary(gopts)


    def currentValues(self, paths):
        "fill out full path and call to server"
        if self.renderurl.startswith("http"):
            url = basicAuthUrl(self.renderuser, self.renderpass,
                                self.renderurl)
            server = xmlrpclib.Server(url)
        else:
            server = self.unrestrictedTraverse(self.renderurl)
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


InitializeClass(PerformanceConf)
