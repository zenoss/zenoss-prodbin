#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################
__doc__="""__init__

Initialize the Confmon Product

Products must follow the following standard
The name of the module (file) and the name of the product class inside
the file must be the same.

If there is a ZMI add screen it must be called "add" + class name (ie addDevice)and it must be defined at the module level.

the class factory must be a function at the module level called 
manage_add + class name (ie manage_addDevice)

If there is an icon for the product it should be called class name + _icon.gif

$Id: __init__.py,v 1.50 2004/04/06 02:19:04 edahl Exp $"""

__version__ = "$Revision: 1.50 $"[11:-2]

import os
import logging
log = logging.getLogger("zen")

from AccessControl import ModuleSecurityInfo

from Products.CMFCore.DirectoryView import registerDirectory

confmon_globals = globals()

productNames = (
    "Classification",
    "Classifier",
    "ClassifierEntry",
    "PerformanceReport",
    "CPU",
    "DataRoot",
    "Device",
    "DeviceClass",
    "DeviceGroup",
    "DeviceHW",
    "DeviceReport",
    "ExpansionCard",
    "FileSystem",
    "HardDisk",
    "Hardware",
    "HardwareClass",
    "IpAddress",
    "IpInterface",
    "IpNetwork",
    "IpRouteEntry",
    "IpService",
    "IpServiceClass",
    "Location",
    "Manufacturer",
    "ManufacturerRoot",
    "MEProduct",
    "MibModule",
    "MibNode",
    "MibNotification",
    "MibOrganizer",
    "MonitorClass",
    "OperatingSystem",
    "OSProcess",
    "OSProcessClass",
    "OSProcessOrganizer",
    "ProductClass",
    "Report",
    "ReportClass",
    "RRDDataSource",
    "RRDGraph",
    "RRDTemplate",
    "RRDThreshold",
    "ServiceClass",
    "ServiceOrganizer",
    "Software",
    "SoftwareClass",
    "StatusMonitorConf",
    "System",
    "UserSettings",
    "WinService",
    "ZDeviceLoader",
    "ZentinelPortal",
    "ZenossInfo",
)

# Make the skins available as DirectoryViews.
registerDirectory('skins', globals())
registerDirectory('help', globals())


confmonModules = []
def loadConfmonModules():
    # import all modules
    for product in productNames:
        mod = __import__(product, globals(), locals(), [])
        confmonModules.append(mod)


def initialize(registrar):
    contentClasses = ()
    contentConstructors = ()

    registrar.registerHelp()
    registrar.registerHelpTitle('Zentinel Portal Help')
    
    if not confmonModules: loadConfmonModules()
    # register products with zope
    for module in confmonModules:
        args = []
        kwargs = {}
        className = module.__name__.split('.')[-1]
        addDtmlName = "add%s" % className
        factoryName = "manage_add%s" % className
        iconName = "www/%s_icon.gif" % className
        confclass = getattr(module, className, None)
        #contentClasses.append(confclass)
        if not confclass: continue
        args.append(confclass)
        constructors = []
        addDtml = getattr(module, addDtmlName, None)
        if addDtml: constructors.append(addDtml)
        factory = getattr(module, factoryName, None)
        if factory: constructors.append(factory)
        if not constructors: continue
        kwargs['constructors'] = constructors
        kwargs['permission'] = "Add DMD Objects"
        if os.path.exists(os.path.join(__path__[0], iconName)):
            kwargs['icon'] = iconName
        log.debug("Register Class=%s",className)
        log.debug("kwargs=%s", constructors)
        apply(registrar.registerClass, args, kwargs)

# XXX
# This is a hack-workaround for PAS until their login form becomes something
# users can easily update
# 
# We need this here so that when Zenoss' Zope is restarted, any changes to the
# file are loaded into the CookieAuthHelper instance.
from AccessControl.Permissions import view
from Products.PageTemplates.ZopePageTemplate import ZopePageTemplate

def refreshLoginForm(context, instanceName='cookieAuthHelper'):
    '''
    'context' should be an acl_users PAS instance.
    '''
    try:
        helper = getattr(context, instanceName)
    except AttributeError:
        # there expected plugin instance is not here
        return
    objId = 'login_form'

    # let's get the data from the file
    filename = os.path.join(os.path.dirname(__file__), 'skins', 'zenmodel',
        '%s.pt' % objId)
    html = open(filename).read()
    # if there is no difference between the file and the object, our job is
    # done; if there is a difference, update the object with the text from the
    # file system.
    if objId in helper.objectIds():
        zpt = helper._getOb(objId)
        if zpt and zpt.read() == html:
            return
        else:
            zpt.write(html)
            return

    # create a new form
    login_form = ZopePageTemplate(id=objId, text=html)
    login_form.title = 'Zenoss Login Form'
    login_form.manage_permission(view, roles=['Anonymous'], acquire=1)
    helper._setObject(objId, login_form, set_owner=0)

def updateACLUsersLoginForms():
    # XXX need to figure out how to run this so that it doesn't hang zenmigrate
    # but still runs when ZenModel is loaded/imported.
    from Products.ZenUtils.ZCmdBase import ZCmdBase
    dmd = ZCmdBase(noopts=True).dmd
    app = dmd.getPhysicalRoot()
    zport = app.zport
    for context in [app.acl_users, zport.acl_users]:
        refreshLoginForm(context)
