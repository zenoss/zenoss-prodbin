#################################################################
#
#   Copyright (c) 2003 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""RRDDataSource

Defines attributes for how a datasource will be graphed
and builds the nessesary DEF and CDEF statements for it.

$Id: RRDDataSource.py,v 1.6 2003/06/03 18:47:49 edahl Exp $"""

__version__ = "$Revision: 1.6 $"[11:-2]

import os
import md5

from Globals import DTMLFile
from Globals import InitializeClass
from DateTime import DateTime
from Acquisition import aq_parent
from AccessControl import ClassSecurityInfo, Permissions

from Products.PageTemplates.Expressions import getEngine

from Products.ZenUtils.ZenTales import talesCompile
from Products.ZenRelations.RelSchema import *
from Products.ZenEvents.ZenEventClasses import Status_Web, Cmd_Fail

from ZenModelRM import ZenModelRM
from ZenPackable import ZenPackable


def manage_addRRDDataSource(context, id, REQUEST = None):
    """make a RRDDataSource"""
    ds = RRDDataSource(id)
    context._setObject(ds.id, ds)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
                                     

addRRDDataSource = DTMLFile('dtml/addRRDDataSource',globals())


def convertMethodParameter(value, type):
    if type == "integer":
        return int(value)
    elif type == "string":
        return str(value)
    elif type == "float":
        return float(value)
    else:
        raise TypeError('Unsupported method parameter type: %s' % type)

def checkOid(oid):
    import string
    for c in string.whitespace:
        oid = oid.replace(c, '')
    oid = oid.strip('.')
    numbers = oid.split('.')
    map(int, numbers)
    if len(numbers) < 3:
        raise ValueError("OID too short")
    return oid



class RRDDataSourceError(Exception): pass


class RRDDataSource(ZenModelRM, ZenPackable):

    meta_type = 'RRDDataSource'

    sourcetypes = ('SNMP', 'XMLRPC', 'COMMAND') # , 'PAGECHECK')
    paramtypes = ('integer', 'string', 'float')

    sourcetype = 'SNMP'
    oid = ''
    xmlrpcURL = ''
    xmlrpcUsername = ''
    xmlrpcPassword = ''
    xmlrpcMethodName = ''
    # [[param1, int], [param2, string], ...]
    xmlrpcMethodParameters = []

    enabled = True
    usessh = False
    component = ''
    eventClass = ''
    eventKey = ''
    severity = 3
    commandTemplate = ""
    cycletime = 300

    # PAGECHECK-specific attrs
    userAgent = ''
    recording = None
    initialURL = ''
    commandHash = ''

    _properties = (
        {'id':'sourcetype', 'type':'selection',
        'select_variable' : 'sourcetypes', 'mode':'w'},
        {'id':'oid', 'type':'string', 'mode':'w'},
        {'id':'xmlrpcURL', 'type':'string', 'mode':'w'},
        {'id':'xmlrpcUsername', 'type':'string', 'mode':'w'},
        {'id':'xmlrpcPassword', 'type':'string', 'mode':'w'},
        {'id':'xmlrpcMethodName', 'type':'string', 'mode':'w'},
        {'id':'xmlrpcMethodParameters', 'type':'lines', 'mode':'w'},

        {'id':'enabled', 'type':'boolean', 'mode':'w'},
        {'id':'usessh', 'type':'boolean', 'mode':'w'},
        {'id':'component', 'type':'string', 'mode':'w'},
        {'id':'eventClass', 'type':'string', 'mode':'w'},
        {'id':'eventKey', 'type':'string', 'mode':'w'},
        {'id':'severity', 'type':'int', 'mode':'w'},
        {'id':'commandTemplate', 'type':'string', 'mode':'w'},
        {'id':'cycletime', 'type':'int', 'mode':'w'},
        
        # PAGECHECK-specific props
        {'id':'userAgent', 'type':'string', 'mode':'w'},
        {'id':'recording', 'type':'file', 'mode':'w'},
        {'id':'initialURL', 'type':'string', 'mode':'w'},
        
        )

    _relations = ZenPackable._relations + (
        ("rrdTemplate", ToOne(ToManyCont,"RRDTemplate","datasources")),
        ("datapoints", ToManyCont(ToOne,"RRDDataPoint","datasource")),
        )
    
    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
    { 
        'immediate_view' : 'editRRDDataSource',
        'actions'        :
        ( 
            { 'id'            : 'edit'
            , 'name'          : 'Data Source'
            , 'action'        : 'editRRDDataSource'
            , 'permissions'   : ( Permissions.view, )
            },
        )
    },
    )

    security = ClassSecurityInfo()


    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object add ActionRules list.
        [('url','id'), ...]
        """
        from RRDTemplate import crumbspath
        crumbs = super(RRDDataSource, self).breadCrumbs(terminator)
        return crumbspath(self.rrdTemplate(), crumbs, -2)

    def getCommandHash(self):
        """The hash is used to generate unique ids and file names."""
        md5hash = md5.new()
        md5hash.update(self.commandTemplate)
        return md5hash.hexdigest()

    def getOidOrUrl(self):
        if self.sourcetype == "SNMP":
            return self.oid
        if self.sourcetype == "XMLRPC":
            return self.xmlrpcURL+" ("+self.xmlrpcMethodName+")"
        if self.sourcetype == "COMMAND":
            if self.usessh:
                return self.commandTemplate + " over SSH"
            else:
                return self.commandTemplate
        if self.sourcetype == 'PAGECHECK':
            md5hash = self.getCommandHash()
            url = "%s#%s" % (self.initialURL, md5hash)
            return url
        return None


    def getXmlRpcMethodParameters(self):
        """Return the list of all parameters as a list.
           ["param1 (type)", "param2 (type)", ...]
        """
        params = []
        for param in self.xmlrpcMethodParameters: 
            p = "%s (%s)" % (param[0], param[1])
            params.append(p)
        return params


    def getRRDDataPoints(self):
        return self.datapoints()


    def manage_addRRDDataPoint(self, id, REQUEST = None):
        """make a RRDDataPoint"""
        if not id:
            return self.callZenScreen(REQUEST)
        from Products.ZenModel.RRDDataPoint import RRDDataPoint
        dp = RRDDataPoint(id)
        self.datapoints._setObject(dp.id, dp)
        if REQUEST: 
            return self.callZenScreen(REQUEST)


    def manage_deleteRRDDataPoints(self, ids=(), REQUEST=None):
        """Delete RRDDataPoints from this RRDDataSource"""

        def clean(rel, id):
            for obj in rel():
                if id in obj.dsnames:
                    obj.dsnames.remove(id)
                    if not obj.dsnames:
                        rel._delObject(obj.id)

        if not ids: return self.callZenScreen(REQUEST)
        for id in ids:
            dp = getattr(self.datapoints,id,False)
            if dp:
                clean(self.graphs, dp.name())
                clean(self.thresholds, dp.name())
                self.datapoints._delObject(dp.id)
        if REQUEST: 
            return self.callZenScreen(REQUEST)


    def getCommand(self, context):
        """Return localized command target.
        """
        # Perform a TALES eval on the expression using self
        exp = "string:"+ self.commandTemplate
        compiled = talesCompile(exp)    
        d = context.device()
        environ = {'dev' : d,
                   'devname': d.id,
                   'here' : context, 
                   'zCommandPath' : context.zCommandPath,
                   'nothing' : None,
                   'now' : DateTime() }
        res = compiled(getEngine().getContext(environ))
        if isinstance(res, Exception):
            raise res
        if self.sourcetype == 'PAGECHECK':
            exp = "string:" + self.initialURL
            compiled = talesCompile(exp)
            initialURL = compiled(getEngine().getContext(environ))
            if isinstance(initialURL, Exception):
                raise initialURL
            go = "go %s\n" % initialURL
            if self.userAgent:
                go += 'agent "%s"\n' % self.userAgent
            res = go + res
            pgm = os.path.join(os.environ['ZENHOME'], 'bin', 'testgen-twill')
            res = "%s -q - << EOF\n%s\nEOF\n" % (pgm, res)
        elif not res.startswith('/'):
            if not res.startswith(context.zCommandPath):
                res = os.path.join(context.zCommandPath, res)
        return res


    def getSeverityString(self):
        return self.ZenEventManager.getSeverityString(self.severity)


    def zmanage_editProperties(self, REQUEST=None):
        'add some validation'
        if REQUEST:
            oid = REQUEST.get('oid', '')
            if oid:
                REQUEST.form['oid'] = checkOid(oid)
            # convert recording to twill-sh commands; there's no need to save
            # the TestGen4Web XML file in the ZODB
            if REQUEST.get('sourcetype') == 'COMMAND':
                if REQUEST.form.get('eventClass', '/') == '/':
                    REQUEST.form['eventClass'] = Cmd_Fail
            recording = REQUEST.get('recording')
            if recording:
                from testgen import twillshell
                data = recording.read()
                initialURL = twillshell.getInitialURL(data)
                commands = twillshell.getTwillShellCommands(data,
                    userAgent=False, debug=False, initialGo=False)
                REQUEST.form['initialURL'] = initialURL
                REQUEST.form['commandTemplate'] = commands
                REQUEST.form['recording'] = ''
            # ensure that PAGECHECK has the default datapoint
            if REQUEST.get('sourcetype') == 'PAGECHECK':
                if not hasattr(self.datapoints, 'totalTime'):
                    self.manage_addRRDDataPoint('totalTime')
                # and eventClass
                if REQUEST.form.get('eventClass', '/') == '/':
                    REQUEST.form['eventClass'] = Status_Web
        return ZenModelRM.zmanage_editProperties(self, REQUEST)
