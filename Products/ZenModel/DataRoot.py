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

__doc__="""DataRoot

DataRoot is the object manager which contains all confmon
data objects.  It can be used as a global acquisition 
name space.
"""

import re
from AccessControl import ClassSecurityInfo
from AccessControl import getSecurityManager
from OFS.OrderedFolder import OrderedFolder
from Globals import DTMLFile
from Globals import InitializeClass
from Globals import DevelopmentMode
from Products.ZenModel.SiteError import SiteError
from Products.ZenModel.ZenModelBase import ZenModelBase
from Products.ZenModel.ZenMenuable import ZenMenuable
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.IpUtil import IpAddressError
from Commandable import Commandable
import socket
import os
import sys
from sets import Set
import string

from Products.ZenUtils.Utils import zenPath, binPath
from Products.ZenUtils.Utils import extractPostContent
from Products.ZenUtils.Utils import json

from Products.ZenEvents.Exceptions import *

from ZenModelRM import ZenModelRM
from ZenossSecurity import ZEN_COMMON, ZEN_MANAGE_DMD

def manage_addDataRoot(context, id, title = None, REQUEST = None):
    """make a device"""
    dr = DataRoot(id, title)
    context._setObject(id, dr)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main')
                                     

addDataRoot = DTMLFile('dtml/addDataRoot',globals())

__pychecker__='no-override'

class DataRoot(ZenModelRM, OrderedFolder, Commandable, ZenMenuable):
    
    meta_type = portal_type = 'DataRoot'

    manage_main = OrderedFolder.manage_main

    manage_options = OrderedFolder.manage_options

    #setTitle = DTMLFile('dtml/setTitle',globals())

    uuid = None
    availableVersion = None
    lastVersionCheck = 0
    lastVersionCheckAttempt = 0
    versionCheckOptIn = True
    reportMetricsOptIn = True
    acceptedTerms = True
    smtpHost = 'localhost'
    pageCommand = '$ZENHOME/bin/zensnpp localhost 444 $RECIPIENT'
    smtpPort = 25
    smtpUser = ''
    smtpPass = ''
    smtpUseTLS = 0
    emailFrom = ''
    iconMap = {}
    geomapapikey = ''
    geocache = ''
    version = ""

    _properties=(
        {'id':'title', 'type': 'string', 'mode':'w'},
        {'id':'prodStateDashboardThresh','type':'int','mode':'w'},
        {'id':'prodStateConversions','type':'lines','mode':'w'},
        {'id':'priorityConversions','type':'lines','mode':'w'},
        {'id':'priorityDashboardThresh','type':'int','mode':'w'},
        {'id':'statusConversions','type':'lines','mode':'w'},
        {'id':'interfaceStateConversions','type':'lines','mode':'w'},
        {'id':'administrativeRoles','type':'lines','mode':'w'},
        {'id':'uuid', 'type': 'string', 'mode':'w'},
        {'id':'availableVersion', 'type': 'string', 'mode':'w'},
        {'id':'lastVersionCheck', 'type': 'long', 'mode':'w'},
        {'id':'lastVersionCheckAttempt', 'type': 'long', 'mode':'w'},
        {'id':'versionCheckOptIn', 'type': 'boolean', 'mode':'w'},
        {'id':'reportMetricsOptIn', 'type': 'boolean', 'mode':'w'},
        {'id':'smtpHost', 'type': 'string', 'mode':'w'},
        {'id':'smtpPort', 'type': 'int', 'mode':'w'},
        {'id':'pageCommand', 'type': 'string', 'mode':'w'},
        {'id':'smtpUser', 'type': 'string', 'mode':'w'},
        {'id':'smtpPass', 'type': 'string', 'mode':'w'},
        {'id':'smtpUseTLS', 'type': 'int', 'mode':'w'},
        {'id':'emailFrom', 'type': 'string', 'mode':'w'},
        {'id':'geomapapikey', 'type': 'string', 'mode':'w'},
        {'id':'geocache', 'type': 'string', 'mode':'w'},
        )

    _relations =  (
        ('userCommands', ToManyCont(ToOne, 'Products.ZenModel.UserCommand', 'commandable')),
        # packs is depracated.  Has been moved to dmd.ZenPackManager.packs
        # Should be removed post Zenoss 2.2
        # TODO
        ('packs',        ToManyCont(ToOne, 'Products.ZenModel.ZenPack',     'root')),
        ('zenMenus', ToManyCont(
            ToOne, 'Products.ZenModel.ZenMenu', 'menuable')),
       )

    # Screen action bindings (and tab definitions)
    factory_type_information = (
        {
            'id'             : 'DataRoot',
            'meta_type'      : 'DataRoot',
            'description'    : """Arbitrary device grouping class""",
            'icon'           : 'DataRoot_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addStatusMonitorconf',
            'immediate_view' : 'Dashboard',
            'actions'        :
            (
                { 'id'            : 'settings'
                , 'name'          : 'Settings'
                , 'action'        : 'editSettings'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Commands'
                , 'action'        : 'dataRootManage'
                , 'permissions'   : ('Manage DMD',)
                },
                { 'id'            : 'users'
                , 'name'          : 'Users'
                , 'action'        : 'ZenUsers/manageUserFolder'
                , 'permissions'   : ( 'Manage DMD', )
                },
                { 'id'            : 'packs'
                , 'name'          : 'ZenPacks'
                , 'action'        : 'ZenPackManager/viewZenPacks'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'menus'
                , 'name'          : 'Menus'
                , 'action'        : 'editMenus'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'portlets'
                , 'name'          : 'Portlets'
                , 'action'        : 'editPortletPerms'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'daemons'
                , 'name'          : 'Daemons'
                , 'action'        : '../About/zenossInfo'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'versions'
                , 'name'          : 'Versions'
                , 'action'        : '../About/zenossVersions'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'backups'
                , 'name'          : 'Backups'
                , 'action'        : 'backupInfo'
                , 'permissions'   : ( "Manage DMD", )
                },
            )
          },
        )

    security = ClassSecurityInfo()

    # production state threshold at which devices show on dashboard
    prodStateDashboardThresh = 1000
    
    # priority threshold at which devices show on dashboard
    priorityDashboardThresh = 2

    prodStateConversions = [
                'Production:1000',
                'Pre-Production:500',
                'Test:400',
                'Maintenance:300',
                'Decommissioned:-1',
                ]

    priorityConversions = [
                'Highest:5',
                'High:4',
                'Normal:3',
                'Low:2',
                'Lowest:1',
                'Trivial:0',
                ]

    statusConversions = [
                'Up:0',
                'None:-1',
                'No DNS:-2',
                ]

    interfaceStateConversions = [
                'up:1',
                'down:2',
                'testing:3',
                'unknown:4',
                'dormant:5',
                'notPresent:6',
                'lowerLayerDown:7',
                ]

    administrativeRoles = (
        "Administrator",
        "Analyst",
        "Engineer",
        "Tester",
    )

    defaultDateRange = 129600 
    performanceDateRanges = [
        ('Hourly',129600,),
        ('Daily',864000,),
        ('Weekly',3628800,),
        ('Monthly',41472000,),
        ('Yearly',62208000,)
    ]


    # when calculating the primary path this will be its root
    zPrimaryBasePath = ("", "zport")


    def __init__(self, id, title=None):
        ZenModelRM.__init__(self, id, title)
        from ZVersion import VERSION
        self.version = "Zenoss " + VERSION


    def getEventCount(self, **kwargs):
        """Return the current event list for this managed entity.
        """
        return self.ZenEventManager.getEventCount(**kwargs)


    def getDmdRoots(self):
        return filter(lambda o: o.isInTree, self.objectValues())


    def exportXmlHook(self,ofile, ignorerels):
        map(lambda x: x.exportXml(ofile, ignorerels), self.getDmdRoots())
            
    
    security.declareProtected(ZEN_COMMON, 'getProdStateConversions')
    def getProdStateConversions(self):
        """getProdStateConversions() -> return a list of tuples 
        for prodstat select edit box"""
        return self.getConversions(self.prodStateConversions)

    
    security.declareProtected(ZEN_COMMON, 'convertProdState')
    def convertProdState(self, prodState):
        '''convert a numeric production state to a
        textual representation using the prodStateConversions
        map'''
        return self.convertAttribute(prodState, self.prodStateConversions)


    security.declareProtected(ZEN_COMMON, 'getStatusConversions')
    def getStatusConversions(self):
        """get text strings for status field"""
        return self.getConversions(self.statusConversions)


    security.declareProtected(ZEN_COMMON, 'convertStatus')
    def convertStatus(self, status):
        """get text strings for status field"""
        return self.convertAttribute(status, self.statusConversions)

    security.declareProtected(ZEN_COMMON, 'getPriorityConversions')
    def getPriorityConversions(self):
        return self.getConversions(self.priorityConversions)

    security.declareProtected(ZEN_COMMON, 'convertPriority')
    def convertPriority(self, priority):
        return self.convertAttribute(priority, self.priorityConversions)

    security.declareProtected(ZEN_COMMON, 'getInterfaceStateConversions')
    def getInterfaceStateConversions(self):
        """get text strings for interface status"""
        if hasattr(self, 'interfaceStateConversions'):
            return self.getConversions(self.interfaceStateConversions)


    security.declareProtected(ZEN_COMMON, 'convertAttribute')
    def convertAttribute(self, numbValue, conversions):
        '''convert a numeric production state to a
        textual representation using the prodStateConversions
        map'''
        numbValue = int(numbValue)
        for line in conversions:
            line = line.rstrip()
            (name, number) = line.split(':')
            if int(number) == numbValue:
                return name
        return numbValue

    security.declareProtected(ZEN_COMMON, 'convertStatusToDot')
    def convertStatusToDot(self, status):
        colors = ['green', 'yellow', 'orange', 'red']
        try: 
            return colors[status]
        except IndexError:
            return 'grey'

    security.declareProtected(ZEN_COMMON, 'getConversions')
    def getConversions(self, attribute):
        """get the text list of itmes that convert to ints"""
        convs = []
        for item in attribute:
            tup = item.split(':')
            tup[1] = int(tup[1])
            convs.append(tup)
        return convs

    security.declarePublic('filterObjectsRegex')
    def filterObjectsRegex(self, filter, objects,
                            filteratt='id', negatefilter=0):
        """filter a list of objects based on a regex"""
        filter = re.compile(filter).search
        filteredObjects = []
        for obj in objects:
            value = getattr(obj, filteratt, None)
            if callable(value):
                value = value()
            fvalue =  filter(value)
            if (fvalue and not negatefilter) or (not fvalue and negatefilter):
                filteredObjects.append(obj)
        return filteredObjects


    security.declareProtected('View', 'myUserGroups')
    def myUserGroups(self):
        user = self.REQUEST.get('AUTHENTICATED_USER')
        if hasattr(user, 'getGroups'):
            return user.getGroups()
        else:
            return ()


    security.declareProtected('View', 'getAllUserGroups')
    def getAllUserGroups(self):
        return self.acl_users.getGroups()

    def reportError(self):
        ''' send an email to the zenoss error email address
            then send user to a thankyou page or an email error page.
        '''
        if self.smtpHost: host = self.smtpHost
        else: host = None
        port = self.smtpPort and self.smtpPort or 25
        usetls = self.smtpUseTLS
        usr = self.smtpUser
        pwd = self.smtpPass

        mailSent = SiteError.sendErrorEmail(
                    self.REQUEST.errorType,
                    self.REQUEST.errorValue,
                    self.REQUEST.errorTrace,
                    self.REQUEST.errorUrl,
                    self.About.getZenossRevision(),
                    self.About.getZenossVersionShort(),
                    self.REQUEST.contactName,
                    self.REQUEST.contactEmail,
                    self.REQUEST.comments,
                    host, port, usetls, usr, pwd)
        if not mailSent:
            body = SiteError.createReport(
                                self.REQUEST.errorType,
                                self.REQUEST.errorValue,
                                self.REQUEST.errorTrace,
                                self.REQUEST.errorUrl,
                                self.About.getZenossRevision(),
                                self.About.getZenossVersionShort(),
                                True,
                                self.REQUEST.contactName,
                                self.REQUEST.contactEmail,
                                self.REQUEST.comments)
            return self.errorEmailFailure(toAddress=SiteError.ERRORS_ADDRESS,
                                          body=body)
        return self.errorEmailThankYou()


    #security.declareProtected('View', 'writeExportRows')
    def writeExportRows(self, fieldsAndLabels, objects, out=None):
        '''Write out csv rows with the given objects and fields.
        If out is not None then call out.write() with the result and return None
        otherwise return the result.
        Each item in fieldsAndLabels is either a string representing a 
         field/key/index (see getDataField) or it is a tuple of (field, label)
         where label is the string to be used in the first row as label
         for that column.
        Objects can be either dicts, lists/tuples or other objects. Field
         is interpreted as a key, index or attribute depending on what
         object is.
        Method names can be passed instead of attribute/key/indices as field.
         In this case the method is called and the return value is used in
         the export.
        '''
        import csv
        import StringIO
        if out:
            buffer = out
        else:
            buffer = StringIO.StringIO()
        fields = []
        labels = []
        if not fieldsAndLabels:
            fieldsAndLabels = []
        if not objects:
            objects = []
        for p in fieldsAndLabels:
            if isinstance(p, tuple):
                fields.append(p[0])
                labels.append(p[1])
            else:
                fields.append(p)
                labels.append(p)
        writer = csv.writer(buffer)
        writer.writerow(labels)
        def getDataField(thing, field):
            if isinstance(thing, dict):
                value = thing.get(field, '')
            elif isinstance(thing, list) or isinstance(thing, tuple):
                value = thing[int(field)]
            else:
                value = getattr(thing, field, '')
            if isinstance(value, ZenModelBase):
                value = value.id
            elif callable(value):
                value = value()
            if value == None:
                value = ''
            return str(value)
        for o in objects:
            writer.writerow([getDataField(o,f) for f in fields])
        if out:
            result = None
        else:
            result = buffer.getvalue()
        return result


    def getUserCommandTargets(self):
        ''' Called by Commandable.doCommand() to ascertain objects on which
        a UserCommand should be executed.
        '''
        raise NotImplemented
        
        
    def getUrlForUserCommands(self):
        return self.getPrimaryUrlPath() + '/dataRootManage'
        

    def getEmailFrom(self):
        ''' Return self.emailFrom or a suitable default
        '''
        return self.emailFrom or 'zenossuser_%s@%s' % (
            getSecurityManager().getUser().getId(), socket.getfqdn())


    def checkValidId(self, id, prep_id = False):
        """Checks a valid id
        """
        if len(id) > 128:
            return 'ZenPack names can not be longer than 128 characters.'
        allowed = Set(list(string.ascii_letters)
                        + list(string.digits)
                        + ['_'])
        attempted = Set(list(id))
        if not attempted.issubset(allowed):
            return 'Only letters, digits and underscores are allowed' + \
                    ' in ZenPack names.'
        return ZenModelRM.checkValidId(self, id, prep_id)


    def setGeocodeCache(self, REQUEST=None):
        """ Store a JSON representation of
            the Google Maps geocode cache
        """
        cache = extractPostContent(REQUEST)
        try: cache = cache.decode('utf-8')
        except: pass
        self.geocache = cache
        return True

    def clearGeocodeCache(self, REQUEST=None):
        """
        Clear the Google Maps cache.
        """
        self.geocache = ''

    security.declareProtected(ZEN_COMMON, 'getGeoCache')
    def getGeoCache(self, REQUEST=None):
        cachestr = self.geocache
        for char in ('\\r', '\\n'):
            cachestr = cachestr.replace(char, ' ')
        cachestr = cachestr.replace("'", r"\'")
        return cachestr

    def goToStatusPage(self, objid, REQUEST=None):
        """ Find a device or network and redirect 
            to its status page.
        """
        import urllib
        objid = urllib.unquote(objid)
        try:
            devid = objid
            if not devid.endswith('*'): devid += '*'
            obj = self.Devices.findDevice(devid)
        except: 
            obj=None
        if not obj:
            try:
                obj = self.Networks.getNet(objid)
            except IpAddressError:
                return None
        if not obj: return None
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(obj.getPrimaryUrlPath())


    def getXMLEdges(self, objid, depth=1, filter="/"):
        """ Get the XML representation of network nodes
            and edges using the obj with objid as a root
        """
        import urllib
        objid = urllib.unquote(objid)
        try:
            devid = objid
            if not devid.endswith('*'): devid += '*'
            obj = self.Devices.findDevice(devid)
        except: obj=None
        if not obj:
            obj = self.Networks.getNet(objid)
        if not obj:
            return '<graph><Start name="%s"/></graph>' % objid
        return obj.getXMLEdges(int(depth), filter, 
                               start=(obj.id,obj.getPrimaryUrlPath()))


    security.declareProtected(ZEN_MANAGE_DMD, 'getBackupFilesInfo')
    def getBackupFilesInfo(self):
        """
        Retrieve a list of dictionaries describing the files in 
        $ZENHOME/backups.
        """
        import stat
        import os
        import datetime
        import operator
                
        def FmtFileSize(size):
            for power, units in ((3, 'GB'), (2, 'MB'), (1, 'KB')):
                if size > pow(1024, power):
                    fmt = '%.2f %s' % ((size * 1.0)/pow(1024, power), units)
                    break
            else:
                fmt = '%s bytes' % size
            return fmt

        backupsDir = zenPath('backups')
        fileInfo = []
        if os.path.isdir(backupsDir):
            for dirPath, dirNames, fileNames in os.walk(backupsDir):
                dirNames[:] = []
                for fileName in fileNames:
                    filePath = os.path.join(backupsDir, fileName)
                    info = os.stat(filePath)
                    fileInfo.append({
                        'fileName': fileName,
                        'size': info[stat.ST_SIZE],
                        'sizeFormatted': FmtFileSize(info[stat.ST_SIZE]),
                        'modDate': info[stat.ST_MTIME],
                        'modDateFormatted': datetime.datetime.fromtimestamp(
                                info[stat.ST_MTIME]).strftime(
                                '%c'),
                        })
        fileInfo.sort(key=operator.itemgetter('modDate'))
        return fileInfo


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_createBackup')
    def manage_createBackup(self, includeEvents=None, includeMysqlLogin=None,
            timeout=120, REQUEST=None):
        """
        Create a new backup file using zenbackup and the options specified
        in the request.
        
        This method makes use of the fact that DataRoot is a Commandable
        in order to use Commandable.write
        """
        import popen2
        import fcntl
        import time
        import select
        
        def write(s):
            if REQUEST:
                self.write(REQUEST.RESPONSE, s)

        if REQUEST:
            header, footer = self.commandOutputTemplate().split('OUTPUT_TOKEN')
            REQUEST.RESPONSE.write(str(header))        
        write('')
        try:
            cmd = binPath('zenbackup') + ' -v'
            if not includeEvents:
                cmd += ' --no-eventsdb'
            if includeMysqlLogin:
                cmd += ' --save-mysql-access'
            try:
                timeout = int(timeout)
            except ValueError:
                timeout = 120
            timeout = max(timeout, 1)
            child = popen2.Popen4(cmd)
            flags = fcntl.fcntl(child.fromchild, fcntl.F_GETFL)
            fcntl.fcntl(child.fromchild, fcntl.F_SETFL, flags | os.O_NDELAY)
            endtime = time.time() + timeout
            write('%s' % cmd)
            write('')
            pollPeriod = 1
            firstPass = True
            while time.time() < endtime and (firstPass or child.poll() == -1):
                firstPass = False
                r, w, e = select.select([child.fromchild], [], [], pollPeriod)
                if r:
                    t = child.fromchild.read()
                    # We are sometimes getting to this point without any data
                    # from child.fromchild.  I don't think that should happen
                    # but the conditional below seems to be necessary.
                    if t:
                        write(t)
                    
            if child.poll() == -1:
                write('Backup timed out after %s seconds.' % timeout)
                import signal
                os.kill(child.pid, signal.SIGKILL)

            write('DONE')
        except:
            write('Exception while performing backup.')
            write('type: %s  value: %s' % tuple(sys.exc_info()[:2]))
        write('')
        if REQUEST:
            REQUEST.RESPONSE.write(footer)


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_deleteBackups')
    def manage_deleteBackups(self, fileNames=(), REQUEST=None):
        """
        Delete the specified files from $ZENHOME/backups
        """
        backupsDir = zenPath('backups')
        count = 0
        if os.path.isdir(backupsDir):
            for dirPath, dirNames, dirFileNames in os.walk(backupsDir):
                dirNames[:] = []
                for fileName in fileNames:
                    if fileName in dirFileNames:
                        res = os.remove(os.path.join(dirPath, fileName))
                        if res == 0:
                            count += 1
            if REQUEST:
                REQUEST['messag'] = '%s files deleted' % count
        else:
            if REQUEST:
                REQUEST['message'] = 'Unable to find $ZENHOME/backups'
        if REQUEST:
            return self.callZenScreen(REQUEST)


    def getProductName(self):
        """
        Return a string that represents the Zenoss product that is installed.
        Currently this is something like 'core' or 'enterprise'.  This is
        used in the version check code to retrieve the available version
        for the correct product.
        """
        return getattr(self, 'productName', 'core')


    def error_handler(self, error=None):
        """
        Returns pretty messages when errors are raised in templates.

        Access this method from a template like so:
            <div tal:content="..."
                 ...
                 tal:on-error="structure python:here.dmd.error_handler(error)">

        @param error: A TALES.ErrorInfo instance with attributes type, value
                      and traceback.
        @return: HTML fragment with an error message
        """
        if error.type==MySQLConnectionError:
            msg = "Unable to connect to the MySQL server."

        elif error.type in [ pythonThresholdException, rpnThresholdException ]:
            msg= error.value

        else: 
            raise 

        return '<b class="errormsg">%s</b>' % msg

    @json
    def isDebugMode(self):
        """
        Whether we're in debug mode, so that javascript will behave accordingly
        """
        return DevelopmentMode

    def versionId(self):
        """
        Get a string representative of the code version, to override JS
        caching.
        """
        return self.About.getZenossVersion().full().replace(
            'Zenoss','').replace(' ','').replace('.','')


InitializeClass(DataRoot)
