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
from Products.ZenModel.OSProcessOrganizer import OSProcessOrganizer
from Products.ZenModel.ServiceOrganizer import ServiceOrganizer
from Products.ZenModel.System import System
from Products.ZenModel.MonitorClass import MonitorClass
from Products.ZenModel.ReportClass import ReportClass
from Products.ZenModel.DataRoot import DataRoot
from Products.ZenModel.ZDeviceLoader import manage_addZDeviceLoader
from Products.ZenModel.ZenossInfo import manage_addZenossInfo
from Products.ZenWidgets.ZenTableManager import manage_addZenTableManager
from Products.ZenModel.PerformanceConf import manage_addPerformanceConf
from Products.ZenModel.StatusMonitorConf import manage_addStatusMonitorConf
from Products.ZenRRD.RenderServer import manage_addRenderServer
from Products.ZenReports.ReportServer import manage_addReportServer
from Products.ZenEvents.MySqlEventManager import manage_addMySqlEventManager
from Products.ZenEvents.EventClass import manage_addEventClass
from Products.CMFCore.DirectoryView import manage_addDirectoryView
from Products.ZenModel.UserSettings import manage_addUserSettingsManager

classifications = {
    'Devices':          DeviceClass,
    'Groups':           DeviceGroup,
    'Locations':        Location,
    'Systems':          System,
    'Services':         ServiceOrganizer,
    'Manufacturers':    ManufacturerRoot,
    'Mibs':             MibOrganizer,
    'Processes':        OSProcessOrganizer,
    'Monitors':         MonitorClass,
    'Reports':          ReportClass,
}

class DmdBuilder:
   
    # Top level organizers for dmd
    dmdroots = (
        'Devices',
        'Groups',
        'Locations',
        'Systems',
        'Services',
        'Processes',
        'Manufacturers',
        'Mibs',
        'Monitors',
        'Reports',
        )
   
    # default monitor classes
    monRoots = ('StatusMonitors','Performance')


    def __init__(self, portal, evthost, evtuser, evtpass, evtdb, 
                    smtphost, smtpport, snpphost, snppport):
        self.portal = portal
        self.evthost = evthost
        self.evtuser = evtuser
        self.evtpass = evtpass
        self.evtdb = evtdb
        dmd = DataRoot('dmd')
        self.portal._setObject(dmd.id, dmd)
        self.dmd = self.portal._getOb('dmd')
        self.dmd.smtpHost = smtphost
        self.dmd.snppHost = snpphost
        self.dmd.smtpPort = smtpport
        self.dmd.snppPort = snppport


    def buildRoots(self):
        self.addroots(self.dmd, self.dmdroots, isInTree=True)
        self.dmd.Devices.buildDeviceTreeProperties()


    def buildMonitors(self):
        mons = self.dmd.Monitors
        self.addroots(mons, self.monRoots, "Monitors")
        mons.Performance.sub_class = 'PerformanceConf'
        mons.StatusMonitors.sub_class = 'StatusMonitorConf'
        manage_addPerformanceConf(mons.Performance, "localhost")
        crk = mons.Performance._getOb("localhost")
        crk.renderurl = "/zport/RenderServer"
        manage_addStatusMonitorConf(mons.StatusMonitors,"localhost")


    def buildUserCommands(self):
        for id, cmd in (
                ('ping', 'ping -c2 ${device/manageIp}'),
                ('traceroute', 'traceroute -q1 -w2 ${device/manageIp}'),
                ('DNS forward', 'host ${device/manageIp}'),
                ('DNS reverse', 'host ${device/id}'),
                ('snmpwalk', 'snmpwalk -v1 -c${device/zSnmpCommunity}'
				' ${here/manageIp} system'),
                ):
            self.dmd.manage_addUserCommand(id, cmd=cmd)

        
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
        self.buildUserCommands()
        manage_addEventClass(self.dmd)
        manage_addZDeviceLoader(self.dmd)
        manage_addZenTableManager(self.portal)
        manage_addZenossInfo(self.portal)
        manage_addDirectoryView(self.portal,'ZenUtils/js', 'js')
        manage_addRenderServer(self.portal, "RenderServer")
        manage_addReportServer(self.portal, "ReportServer")
        manage_addMySqlEventManager(self.dmd, evthost=self.evthost,
                                    evtuser=self.evtuser, evtpass=self.evtpass,
                                    evtdb=self.evtdb)
        manage_addMySqlEventManager(self.dmd, evthost=self.evthost,
                                    evtuser=self.evtuser, evtpass=self.evtpass,
                                    evtdb=self.evtdb, 
                                    history=True)
        manage_addUserSettingsManager(self.dmd)
        manage_addIpNetwork(self.dmd, "Networks")

