#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
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

from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.Location import Location
from Products.ZenModel.DeviceGroup import DeviceGroup
from Products.ZenModel.ProductClass import ProductClass
from Products.ZenModel.IpNetwork import manage_addIpNetwork
from Products.ZenModel.ManufacturerRoot import ManufacturerRoot
from Products.ZenModel.MibOrganizer import MibOrganizer
from Products.ZenModel.ServiceOrganizer import ServiceOrganizer
from Products.ZenModel.System import System
from Products.ZenModel.MonitorClass import MonitorClass
from Products.ZenModel.ReportClass import ReportClass
from Products.ZenModel.DataRoot import DataRoot
from Products.ZenModel.ZDeviceLoader import manage_addZDeviceLoader
from Products.ZenWidgets.ZenTableManager import manage_addZenTableManager
from Products.ZenModel.PerformanceReport import manage_addPerformanceReport
from Products.ZenModel.PerformanceConf import manage_addPerformanceConf
from Products.ZenModel.StatusMonitorConf import manage_addStatusMonitorConf
from Products.ZenRRD.RenderServer import manage_addRenderServer
from Products.ZenEvents.MySqlEventManager import manage_addMySqlEventManager
from Products.ZenEvents.EventClass import manage_addEventClass
from Products.CMFCore.DirectoryView import manage_addDirectoryView
from Products.ZenModel.UserSettings import manage_addUserSettingsManager

classifications = {
    'Devices':      DeviceClass,
    'Groups':       DeviceGroup,
    'Locations':    Location,
    'Systems':      System,
    'Services':     ServiceOrganizer,
    'Manufacturers':    ManufacturerRoot,
    'Mibs':         MibOrganizer,
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
        'Manufacturers',
        'Mibs',
        'Monitors', 
        'Reports',
        )
   
    # default monitor classes
    monRoots = ('StatusMonitors','Performance')


    def __init__(self, portal, evtuser, evtpass):
        self.portal = portal
        self.evtuser = evtuser
        self.evtpass = evtpass
        dmd = DataRoot('dmd')
        self.portal._setObject(dmd.id, dmd)
        self.dmd = self.portal._getOb('dmd')


    def buildRoots(self):
        self.addroots(self.dmd, self.dmdroots, isInTree=True)
        self.dmd.Devices.buildDeviceTreeProperties()


    def buildMonitors(self):
        mons = self.dmd.Monitors
        self.addroots(mons, self.monRoots, "Monitors")
        manage_addPerformanceConf(mons.Performance, "localhost")
        crk = mons.Performance._getOb("localhost")
        crk.renderurl = "/zport/RenderServer"
        manage_addStatusMonitorConf(mons.StatusMonitors,"localhost")


    def buildServices(self):
        srvs = self.dmd.Services
        srvRoots = ('IpServices',)
        self.addroots(srvs, srvRoots, "Services")


    def addroots(self, base, rlist, classType=None, isInTree=False):
        for rname in rlist:
            ctype = classType or rname
            if not hasattr(base, rname):
                dr = classifications[ctype](rname)
                base._setObject(dr.id, dr)
                dr = base._getOb(dr.id)
                dr.isInTree = isInTree
                if dr.id in ('Devices'):
                    dr.createCatalog() 


    def build(self):
        self.buildRoots()
        self.buildMonitors()
        self.buildServices()
        manage_addEventClass(self.dmd)
        manage_addZDeviceLoader(self.dmd)
        manage_addPerformanceReport(self.dmd)
        manage_addZenTableManager(self.portal)
        manage_addDirectoryView(self.portal,'ZenUtils/js', 'js')
        manage_addRenderServer(self.portal, "RenderServer")
        manage_addMySqlEventManager(self.dmd, evtuser=self.evtuser, 
                                              evtpass=self.evtpass)
        manage_addMySqlEventManager(self.dmd, evtuser=self.evtuser,
                                    evtpass=self.evtpass, history=True)
        manage_addUserSettingsManager(self.dmd)
        manage_addIpNetwork(self.dmd, "Networks")
                                    
