#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""DmdBuilder

DmdBuilder builds out the core containment structure used in the dmd database.

Devices
Groups
Locations
Networks
ServiceAreas
Services
Systems

$Id: DmdBuilder.py,v 1.11 2004/04/06 22:33:07 edahl Exp $"""

__version__ = "$Revision: 1.11 $"[11:-2]

import sys
import os

import transaction
import Zope2

from OFS.Image import File
from Acquisition import aq_base

from Products.ZenModel.CompanyClass import CompanyClass
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.Location import Location
from Products.ZenModel.DeviceGroup import DeviceGroup
from Products.ZenModel.ProductClass import ProductClass
from Products.ZenModel.IpNetwork import IpNetwork
from Products.ZenModel.ManufacturerRoot import ManufacturerRoot
from Products.ZenModel.ServiceClass import ServiceClass
from Products.ZenModel.System import System
from Products.ZenModel.MonitorClass import MonitorClass
from Products.ZenModel.ReportClass import ReportClass
from Products.ZenModel.DataRoot import DataRoot
from Products.ZenModel.Classifier import manage_addClassifier
from Products.ZenModel.ZDeviceLoader import manage_addZDeviceLoader
from Products.ZenWidgets.ZenTableManager import manage_addZenTableManager
from Products.ZenModel.SnmpClassifier import manage_addSnmpClassifier
from Products.ZenModel.CricketConf import manage_addCricketConf
from Products.ZenModel.StatusMonitorConf import manage_addStatusMonitorConf
from Products.ZenRRD.RenderServer import manage_addRenderServer
from Products.ZenEvents.MySqlEventManager import manage_addMySqlEventManager
from Products.ZenEvents.EventClass import manage_addEventClass
from Products.CMFCore.DirectoryView import manage_addDirectoryView

classifications = {
    'Devices':      DeviceClass,
    'Groups':       DeviceGroup,
    'Locations':    Location,
    'Systems':      System,
    'Services':     ServiceClass,
    'Networks':     IpNetwork,
    'Manufacturers':    ManufacturerRoot,
    'Monitors':     MonitorClass,
    'Reports':      ReportClass,
}

class DmdBuilder:
   
    # Top level organizers for dmd
    dmdroots = (
        'Devices', 
        'Groups', 
        'Locations', 
        'Systems', 
        'Services',
        'Networks', 
        'Manufacturers',
        'Monitors', 
        'Reports',
        )
   
    # default monitor classes
    monRoots = ('StatusMonitors','Cricket')


    deviceClasses = (
        "/Unknown",
        "/NetworkDevice/Router/UBRRouter",
        "/NetworkDevice/Router/TerminalServer",
        "/NetworkDevice/Router/Firewall",
        "/NetworkDevice/Router/RSM",
        "/NetworkDevice/Switch",
        "/NetworkDevice/Switch/ContentSwitch",
        "/NetworkDevice/CableModem",
        "/Server/Linux",
        "/Server/Windows",
        "/Server/Solaris",
        "/Server/Darwin",
        "/Printer/LaserPrinter",
        "/Printer/InkJetPrinter",
        )


    def __init__(self, portal, schema="schema.data"):
        self.portal = portal
        dmd = DataRoot('dmd')
        self.portal._setObject(dmd.id, dmd)
        self.dmd = self.portal._getOb('dmd')
        self.schema = schema


    def buildRoots(self):
        self.addroots(self.dmd, self.dmdroots, isInTree=True)
        self.dmd.Devices.buildDeviceTreeProperties()


    def buildMonitors(self):
        mons = self.dmd.Monitors
        self.addroots(mons, self.monRoots, "Monitors")
        manage_addCricketConf(mons.Cricket, "localhost")
        crk = mons.Cricket._getOb("localhost")
        crk.cricketurl = "/zport/RenderServer"
        crk.cricketroot = os.path.join(os.environ['ZENHOME'], "cricket")
        manage_addStatusMonitorConf(mons.StatusMonitors,"localhost")


    def buildServices(self):
        srvs = self.dmd.Services
        srvRoots = ('IpServices',)
        self.addroots(srvs, srvRoots, "Services")


    def buildDevices(self):
        devices = self.dmd.Devices
        for devicePath in self.deviceClasses:
            devices.createOrganizer(devicePath)


    def addroots(self, base, rlist, classType=None, isInTree=False):
        for rname in rlist:
            ctype = classType or rname
            if not hasattr(base, rname):
                dr = classifications[ctype](rname)
                base._setObject(dr.id, dr)
                dr = base._getOb(dr.id)
                dr.isInTree = isInTree
                if dr.id in ('Devices','Networks'):
                    dr.createCatalog() 


    def buildClassifiers(self):
        if hasattr(self.dmd, 'ZenClassifier'):
            return
        manage_addClassifier(self.dmd)
        cl = self.dmd._getOb('ZenClassifier')
        snmpclassifiers = (
            ('sysObjectIdClassifier', '.1.3.6.1.2.1.1.2.0'),
            ('sysDescrClassifier', '.1.3.6.1.2.1.1.1.0'),
        )
        for sclname, oid in snmpclassifiers:
            manage_addSnmpClassifier(cl, sclname)
            snmpc = cl._getOb(sclname)
            snmpc.oid = oid


    def build(self):
        self.buildClassifiers()
        self.buildRoots()
        self.buildMonitors()
        self.buildServices()
        self.buildDevices()
        manage_addEventClass(self.dmd)
        manage_addZDeviceLoader(self.dmd)
        manage_addZenTableManager(self.portal)
        manage_addDirectoryView(self.portal,'ZenUtils/js', 'js')
        manage_addRenderServer(self.portal, "RenderServer")
        manage_addMySqlEventManager(self.dmd)
        manage_addMySqlEventManager(self.dmd,history=True)
