#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""DataRoot

DataRoot is the object manager which contains all confmon
data objects.  It can be used as a global acquisition 
name space.
"""

import re

from AccessControl import ClassSecurityInfo
from AccessControl import getSecurityManager
from OFS.OrderedFolder import OrderedFolder
from OFS.CopySupport import CopyError, eNotSupported
from ImageFile import ImageFile
from Globals import HTMLFile, DTMLFile
from Globals import InitializeClass
from Acquisition import aq_base
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.ZenModel.SiteError import SiteError
from ImageFile import ImageFile
from Products.ZenModel.ZenModelBase import ZenModelBase
from Products.ZenModel.ZenMenuable import ZenMenuable
from Products.ZenRelations.RelSchema import *
from Commandable import Commandable
import DateTime
import socket

from AccessControl import Permissions as permissions

from ZenModelRM import ZenModelRM

def manage_addDataRoot(context, id, title = None, REQUEST = None):
    """make a device"""
    dr = DataRoot(id, title)
    context._setObject(id, dr)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main')
                                     

addDataRoot = DTMLFile('dtml/addDataRoot',globals())

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
    acceptedTerms = False
    smtpHost = 'localhost'
    snppHost = 'localhost'
    smtpPort = 25
    snppPort = 444
    smtpUser = ''
    smtpPass = ''
    smtpUseTLS = 0
    emailFrom = ''

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
        {'id':'snppHost', 'type': 'string', 'mode':'w'},
        {'id':'snppPort', 'type': 'int', 'mode':'w'},
        {'id':'smtpUser', 'type': 'string', 'mode':'w'},
        {'id':'smtpPass', 'type': 'string', 'mode':'w'},
        {'id':'smtpUseTLS', 'type': 'int', 'mode':'w'},
        {'id':'emailFrom', 'type': 'string', 'mode':'w'},
        )

    _relations =  (
        ('userCommands', ToManyCont(ToOne, 'UserCommand', 'commandable')),
        ('packs',        ToManyCont(ToOne, 'ZenPack',     'root')),
        ('zenMenus', ToManyCont(
            ToOne, 'ZenMenu', 'menuable')),
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
                , 'name'          : 'Manage'
                , 'action'        : 'dataRootManage'
                , 'permissions'   : ('Manage DMD',)
                },
                { 'id'            : 'packs'
                , 'name'          : 'ZenPacks'
                , 'action'        : 'viewZenPacks'
                , 'permissions'   : ( "Manage DMD", )
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
    

    def getResultFields(self):
        """Result fields for dashboard.
        """
        return ('device','summary','lastTime','count')
       

    def getEventList(self, **kwargs):
        """Return the current event list for this managed entity.
        """
        return self.ZenEventManager.getEventList(**kwargs)
        

    def getDmdRoots(self):
        return filter(lambda o: o.isInTree, self.objectValues())


    def exportXmlHook(self,ofile, ignorerels):
        map(lambda x: x.exportXml(ofile, ignorerels), self.getDmdRoots())
            
    
    security.declareProtected('View', 'getProdStateConversions')
    def getProdStateConversions(self):
        """getProdStateConversions() -> return a list of tuples 
        for prodstat select edit box"""
        return self.getConversions(self.prodStateConversions)

    
    security.declareProtected('View', 'convertProdState')
    def convertProdState(self, prodState):
        '''convert a numeric production state to a
        textual representation using the prodStateConversions
        map'''
        return self.convertAttribute(prodState, self.prodStateConversions)


    security.declareProtected('View', 'getStatusConversions')
    def getStatusConversions(self):
        """get text strings for status field"""
        return self.getConversions(self.statusConversions)


    security.declareProtected('View', 'convertStatus')
    def convertStatus(self, status):
        """get text strings for status field"""
        return self.convertAttribute(status, self.statusConversions)

    security.declareProtected('View', 'getPriorityConversions')
    def getPriorityConversions(self):
        return self.getConversions(self.priorityConversions)

    security.declareProtected('View', 'convertPriority')
    def convertPriority(self, priority):
        return self.convertAttribute(priority, self.priorityConversions)

    security.declareProtected('View', 'getInterfaceStateConversions')
    def getInterfaceStateConversions(self):
        """get text strings for interface status"""
        if hasattr(self, 'interfaceStateConversions'):
            return self.getConversions(self.interfaceStateConversions)


    security.declareProtected('View', 'convertAttribute')
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


    security.declareProtected('View', 'getConversions')
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
        mailSent = SiteError.sendErrorEmail(
                    self.REQUEST.errorType,
                    self.REQUEST.errorValue,
                    self.REQUEST.errorTrace,
                    self.REQUEST.errorUrl,
                    self.About.getZenossRevision(),
                    self.REQUEST.contactName,
                    self.REQUEST.contactEmail,
                    self.REQUEST.comments)
        if not mailSent:
            toAddress = SiteError.ERRORS_ADDRESS
            body = SiteError.createReport(
                                self.REQUEST.errorType,
                                self.REQUEST.errorValue,
                                self.REQUEST.errorTrace,
                                self.REQUEST.errorUrl,
                                self.About.getZenossRevision(),
                                True,
                                self.REQUEST.contactName,
                                self.REQUEST.contactEmail,
                                self.REQUEST.comments)
            return getattr(self, 'errorEmailFailure')(
                        toAddress=SiteError.ERRORS_ADDRESS,
                        body=body)
        return getattr(self, 'errorEmailThankYou')()


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
        raise 'Not supported on DataRoot'

    def getEmailFrom(self):
        ''' Return self.emailFrom or a suitable default
        '''
        return self.emailFrom or 'zenossuser_%s@%s' % (
            getSecurityManager().getUser().getId(), socket.getfqdn())

    def manage_addZenPack(self, id,
                          author="",
                          organization="",
                          version="",
                          REQUEST = None):
        """make a new ZenPack"""
        from ZenPack import ZenPackBase
        pack = ZenPackBase(id)
        pack.author = author
        pack.organization = organization
        pack.version = version
        self.packs._setObject(id, pack)
        import os
        zp = os.path.join(os.environ['ZENHOME'], 'Products', id)
        if not os.path.isdir(zp):
            os.makedirs(zp)
            for d in ['objects', 'skins', 'modeler/plugins',
                      'reports', 'daemons']:
                os.makedirs(os.path.join(zp, d))
        if REQUEST is not None:
            return self.callZenScreen(REQUEST, redirect=True)

    def removeZenPacks(self, ids=(), REQUEST = None):
        """remove a ZenPack"""
        import os
        zp = os.path.join(os.environ['ZENHOME'], 'bin', 'zenpack')
        import os
        for pack in ids:
            os.system('%s run --remove %s' % (zp, pack))
        self._p_jar.sync()
        if REQUEST is not None:
            return self.callZenScreen(REQUEST)

InitializeClass(DataRoot)
