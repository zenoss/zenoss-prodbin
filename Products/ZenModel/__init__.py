#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
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

from AccessControl import ModuleSecurityInfo

from Products.CMFCore.permissions import AddPortalContent
from Products.CMFCore.DirectoryView import registerDirectory

confmon_globals = globals()

productNames = (
    "ZentinelPortal",
    "Classification",
    "ArpEntry",
    "CricketReport",
    "DataRoot",
    "Device",
    "DeviceClass",
    "Router",
    "UBRRouter",
    "TerminalServer",
    "Server",
    "IpInterface",
    "HardDisk",
    "FileSystem",
    "System",
    "DeviceGroup",
    "IpService",
    "IpServiceClass",
    "ServiceClass",
    "Location",
    "IpNetwork",
    "IpAddress",
    "IpRouteEntry",
    "Company",
    "CompanyClass",
    "Product",
    "ProductClass",
    "Software",
    "MonitorClass",
    "Hardware",
    "StatusMonitorConf",
    "CricketConf",
    "Classifier",
    "SnmpClassifier",
    "ClassifierEntry",
    "ReportClass",
    "Report",
    "ZDeviceLoader",
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
    from zLOG import LOG, DEBUG
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
        LOG("ZenModel__init__", DEBUG, "Register Class=%s" % className)
        LOG("ZenModel__init__", DEBUG, "kwargs=%s" % constructors)
        apply(registrar.registerClass, args, kwargs)
