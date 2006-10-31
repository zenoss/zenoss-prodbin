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
from OFS.OrderedFolder import OrderedFolder
from OFS.CopySupport import CopyError, eNotSupported
from ImageFile import ImageFile
from Globals import HTMLFile, DTMLFile
from Globals import InitializeClass
from Acquisition import aq_base
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.ZenModel.SiteError import SiteError
from ImageFile import ImageFile
import DateTime

from AccessControl import Permissions as permissions

from ZenModelRM import ZenModelRM

def manage_addDataRoot(context, id, title = None, REQUEST = None):
    """make a device"""
    dr = DataRoot(id, title)
    context._setObject(id, dr)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main')
                                     

addDataRoot = DTMLFile('dtml/addDataRoot',globals())

class DataRoot(ZenModelRM, OrderedFolder):
    meta_type = portal_type = 'DataRoot'

    manage_main = OrderedFolder.manage_main

    manage_options = OrderedFolder.manage_options

    #setTitle = DTMLFile('dtml/setTitle',globals())

    uuid = None
    availableVersion = None
    lastVersionCheck = 0
    versionCheckOptIn = True
    reportMetricsOptIn = True
    acceptedTerms = False

    _properties=(
        {'id':'title', 'type': 'string', 'mode':'w'},
        {'id':'prodStateDashboardThresh','type':'int','mode':'w'},
        {'id':'prodStateConversions','type':'lines','mode':'w'},
        {'id':'statusConversions','type':'lines','mode':'w'},
        {'id':'interfaceStateConversions','type':'lines','mode':'w'},
        {'id':'administrativeRoles','type':'lines','mode':'w'},
        {'id':'uuid', 'type': 'string', 'mode':'w'},
        {'id':'availableVersion', 'type': 'string', 'mode':'w'},
        {'id':'lastVersionCheck', 'type': 'long', 'mode':'w'},
        {'id':'versionCheckOptIn', 'type': 'boolean', 'mode':'w'},
        {'id':'reportMetricsOptIn', 'type': 'boolean', 'mode':'w'},
        )

    # Screen action bindings (and tab definitions)
    factory_type_information = (
        {
            'id'             : 'DataRoot',
            'meta_type'      : 'DataRoot',
            'description'    : """Arbitrary devlastVersionice grouping class""",
            'icon'           : 'DataRoot_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addStatusMonitorconf',
            'immediate_view' : 'Dashboard',
            'actions'        :
            (
                { 'id'            : 'dashboard'
                , 'name'          : 'Dashboard'
                , 'action'        : 'Dashboard'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'settings'
                , 'name'          : 'Settings'
                , 'action'        : 'editSettings'
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

    prodStateConversions = [
                'Production:1000',
                'Pre-Production:500',
                'Test:400',
                'Maintenance:300',
                'Decommissioned:-1',
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
        import Products.ZenUtils.Version as Version
        mailSent = SiteError.sendErrorEmail(
                    self.REQUEST.errorType,
                    self.REQUEST.errorValue,
                    self.REQUEST.errorTrace,
                    self.REQUEST.errorUrl,
                    Version.getZenossRevision(),
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
                                Version.getZenossRevision(),
                                True,
                                self.REQUEST.contactName,
                                self.REQUEST.contactEmail,
                                self.REQUEST.comments)
            return getattr(self, 'errorEmailFailure')(
                        toAddress=SiteError.ERRORS_ADDRESS,
                        body=body)
        return getattr(self, 'errorEmailThankYou')()


InitializeClass(DataRoot)
