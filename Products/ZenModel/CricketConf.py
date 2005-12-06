#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""CricketConf

The configuration object for Cricket

Cricket loads cricket plugins to build a data structor that
is sent to CricketBuilder through web services from which it can
build cricket target configuration files. 

Data structure sent to Cricketbuiler is as follows:

((targetfilepath, ({targetdata},)))

targetfilepath is the path where the targets file should be created
next element is a tuple of target dictionaries. 
each targetdata dictionary contains the key value pairs for that target

$Id: CricketConf.py,v 1.30 2004/04/06 18:16:30 edahl Exp $"""

__version__ = "$Revision: 1.30 $"[11:-2]

import logging
import transaction

import xmlrpclib

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

def manage_addCricketConf(context, id, title = None, REQUEST = None):
    """make a device class"""
    dc = CricketConf(id)
    context._setObject(id, dc)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addCricketConf = DTMLFile('dtml/addCricketConf',globals())

class CricketConf(Monitor, StatusColor):
    '''Configuration for cricket'''
    portal_type = meta_type = "CricketConf"
    
    monitorRootName = "Cricket"

    security = ClassSecurityInfo()
    security.setDefaultAccess('allow')

    _properties = (
        {'id':'cricketroot','type':'string','mode':'w'},
        {'id':'cricketurl','type':'string','mode':'w'},
        {'id':'cricketuser','type':'string','mode':'w'},
        {'id':'cricketpass','type':'string','mode':'w'},
        )
    _relations = Monitor._relations + (
        ("devices", ToMany(ToOne,"Device","cricket")),
        )

    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'id'             : 'CricketConf',
            'meta_type'      : 'CricketConf',
            'description'    : """CricketConf class""",
            'icon'           : 'CricketConf_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addCricketConf',
            'immediate_view' : 'viewCricketConfOverview',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewCricketConfOverview'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
                , 'action'        : 'editCricketConf'
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


    def __init__(self, id):
        Monitor.__init__(self, id)
        self.cricketroot = ''
        self.cricketurl = ''
        self.cricketuser = ''
        self.cricketpass = ''


    security.declareProtected('View','getDevices')
    def getDevices(self):
        '''get the devices associated with this
        ping monitor configuration'''
        devices = []
        for dev in self.devices.objectValuesAll():
            #if dev.productionState == 'Pre-Production':
            devices.append({
                'snmp_community': dev.zSnmpCommunity,
                'name': dev.getParent().id,
                'dns_name': dev.id,
                'url_path': dev.getPrimaryUrlPath()})
        return devices


    def cricketGraphUrl(self, context, targetpath, targettype,
                     view, drange):
        """set the full path of the target and send to view"""
        targetpath = self.getCricketRoot() + '/cricket-data' + targetpath
        gopts =  view.graphOpts(context, targetpath, targettype)
        gopts = url_quote('|'.join(gopts))
        return "%s/render?gopts=%s&drange=%d" % (self.cricketurl,gopts,drange)

 
    def cricketSummary(self, context, targetpath, targettype):
        """set full path of the target send to view to build opts
        and then call RenderServer through xmlrpc to get data"""
        targetpath = self.getCricketRoot() + '/cricket-data' + targetpath
        gopts =  view.summaryOpts(context, targetpath, targettype)
        #do xmlrpc call to get data


    def cricketMGraphUrl(self, context, targetsmap, view, drange):
        """set the full paths for all targts in map and send to view"""
        ntm = []
        for target, targettype in targetsmap:
            if target.find('.rrd') == -1: target += '.rrd'
            fulltarget = self.getCricketRoot() + '/cricket-data' + target
            ntm.append((fulltarget, targettype))
        gopts =  view.multiGraphOpts(context, ntm)
        gopts = url_quote('|'.join(gopts))
        return "%s/render?gopts=%s&drange=%d" % (self.cricketurl,gopts,drange)


    def cricketCustomUrl(self, gopts, drange):
        "return the for a list of custom gopts for a graph"
        gotps = self._fullCricketPath(gopts)
        gopts = url_quote('|'.join(gopts))
        return "%s/render?gopts=%s&drange=%d" % (self.cricketurl,gopts,drange)


    def cricketCustomSummary(self, gopts, drange):
        "fill out full path for custom gopts and call to server"
        gotps = self._fullCricketPath(gopts)
        if self.cricketurl.startswith("http"):
            url = basicAuthUrl(self.cricketuser, self.cricketpass,
                                self.cricketurl)
            server = xmlrpclib.Server(url)
        else:
            server = self.unrestrictedTraverse(self.cricketurl)
        return server.summary(gopts, drange)
        

    def _fullCricketPath(self, gopts):
        "add full path to a list of custom graph options"
        for i in range(len(gopts)):
            opt = gopts[i]
            if opt.find("DEF") == 0:
                opt = opt.split(':')
                var, file = opt[1].split('=')
                file = self.getCricketRoot() + '/cricket-data' + file
                opt[1] = "%s=%s" % (var, file)
                opt = ':'.join(opt)
                gopts[i] = opt
        return gopts
   

    def getCricketRoot(self):
        """the fully qualified path to this cricket server's root"""
        return self.cricketroot


    security.declareProtected('View','cricketDeviceList')
    def cricketDeviceList(self, force=False):
        """Return a list of urls that point to our managed devices"""
        devlist = []
        for dev in self.devices():
            if (force or (not dev.pastSnmpMaxFailures() and 
                dev.getLastChange() > dev.getLastCricketGenerate())):
                devlist.append(dev.getPrimaryUrlPath(full=True))
        return devlist
           

    security.declareProtected('Manage DMD', 'manage_editCricketConf')
    def manage_editCricketConf(self, 
                cricketroot = '', cricketurl = '',
                cricketuser = '', cricketpass = '', REQUEST=None):
        """
        Edit a CricketConfig from a web page.
        """
        self.cricketroot = cricketroot
        self.cricketurl = cricketurl
        self.cricketuser = cricketuser
        self.cricketpass = cricketpass
        if REQUEST:
            REQUEST['message'] = "Saved at time:"
            return self.callZenScreen(REQUEST)



InitializeClass(CricketConf)
