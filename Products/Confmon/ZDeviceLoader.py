###############################################################################
#
#   Copyright (c) 2004 Zentinel Systems. 
#
###############################################################################


__doc__="""ZDeviceLoader.py

load devices from a GUI screen in the ZMI

$Id: ZDeviceLoader.py,v 1.19 2004/04/22 02:14:12 edahl Exp $"""

__version__ = "$Revision: 1.19 $"[11:-2]

import logging
import StringIO

from AccessControl import ClassSecurityInfo

from OFS.SimpleItem import SimpleItem

from Products.SnmpCollector.SnmpCollector import SnmpCollector

from ConfmonItem import ConfmonItem
from Device import manage_createDevice


def manage_addZDeviceLoader(context, id="", REQUEST = None):
    """make a DeviceLoader"""
    if not id: id = "DeviceLoader"
    d = ZDeviceLoader(id)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 


class ZDeviceLoader(ConfmonItem,SimpleItem):
    """Load devices into the DMD database"""

    portal_type = meta_type = 'DeviceLoader'

    manage_options = ((
            {'label':'ManualDeviceLoader', 'action':'manualDeviceLoader'},
            ) + SimpleItem.manage_options)

   
    security = ClassSecurityInfo()


    def __init__(self, id):
        self.id = id


    def __call__(self):
        """addDevice is default screen"""
        return self.addDevice()


    def loadDevice(self, deviceName, devicePath, 
            tag="", serialNumber="",
            snmpCommunity="public", snmpPort=161,
            rackSlot=0, productionState=1000, comments="",
            manufacturer="", model="", 
            locationPath="", rack="",
            groupPaths=[], systemPaths=[],
            statusMonitors=["localhost"], cricketMonitor="localhost",
            REQUEST = None):

        """load a device into the database"""

        if REQUEST:
            response = REQUEST.response
            self.setupLog(response)
        else:
            response = StringIO.StringIO()
        response.write("<html><body bgcolor='#ffffff'><pre>")
        device = None
        try:
            device = manage_createDevice(self, deviceName, devicePath,
                tag, serialNumber,
                snmpCommunity, snmpPort, 
                rackSlot, productionState, comments,
                manufacturer, model, 
                locationPath, rack,
                groupPaths, systemPaths, 
                statusMonitors, cricketMonitor,
                REQUEST)
        except:
            logging.exception('load of device %s failed' % device)
        else:
            get_transaction().commit()
            device.collectConfig()
            logging.info("device %s loaded!" % deviceName)
            self.navlinks(device, response)
        response.write("</pre></body></html>")


    def addManufacturer(self, newManufacturerName, REQUEST=None):
        """add a manufacturer to the database"""
        self.getOrganizer("Companies").getCompany(newManufacturerName)
        if REQUEST:
            self.REQUEST['manufacturer'] = newManufacturerName
            return self.addDevice()


    security.declareProtected('Change Device', 'setModel')
    def setModel(self, manufacturer, newModelName, REQUEST=None):
        """set the model of this device"""
        modelObj = self.getOrganizer("Products").getModelProduct(
                                        manufacturer, newModelName)
        if REQUEST:
            self.REQUEST['model'] = newModelName
            return self.addDevice()


    security.declareProtected('Change Device', 'setLocation')
    def setLocation(self, newLocationPath, REQUEST=None):
        """add a location to the database"""
        self.getOrganizer("Locations").getLocation(newLocationPath)
        if REQUEST:
            self.REQUEST['locationPath'] = newLocationPath
            return self.addDevice()


    security.declareProtected('Change Device', 'setRackLocation')
    def setRackLocation(self, newLocationPath, REQUEST=None):
        """add a rack location to the database"""
        self.getOrganizer("Locations").getRackLocation(newLocationPath)
        if REQUEST:
            self.REQUEST['locationPath'] = newLocationPath
            return self.addDevice()


    security.declareProtected('Change Device', 'addSystem')
    def addSystem(self, newSystemPath, REQUEST=None):
        """add a system to the database"""
        self.getOrganizer("Systems").getSystem(newSystemPath)
        syss = self.REQUEST.get('systemPaths', [])
        syss.append(newSystemPath)
        if REQUEST:
            self.REQUEST['systemPaths'] = syss
            return self.addDevice()


    security.declareProtected('Change Device', 'addDeviceGroup')
    def addDeviceGroup(self, newDeviceGroupPath, REQUEST=None):
        """add a device group to the database"""
        self.getOrganizer("Groups").getDeviceGroup(newDeviceGroupPath)
        groups = self.REQUEST.get('groupPaths', [])
        groups.append(newDeviceGroupPath)
        if REQUEST:
            REQUEST['groupPaths'] = groups
            return self.addDevice()


    security.declareProtected('Change Device', 'addStatusMonitor')
    def addStatusMonitor(self, newStatusMonitor, REQUEST=None):
        """add new status monitor to the database"""
        self.getOrganizer("Monitors").getStatusMonitor(newStatusMonitor)
        mons = self.REQUEST.get('statusMonitors', [])
        mons.append(newStatusMonitor)
        if REQUEST:
            self.REQUEST['statusMonitors'] = mons
            return self.addDevice()


    security.declareProtected('Change Device', 'setCricketMonitor')
    def setCricketMonitor(self, newCricketMonitor, REQUEST=None):
        """add new cricket monitor to the database"""
        self.getOrganizer("Monitors").getCricketMonitor(newCricketMonitor)
        if REQUEST:
            self.REQUEST['cricketMonitor'] = newCricketMonitor
            return self.addDevice()


    def setupLog(self, response):
        """setup logging package to send to browser"""
        from logging import StreamHandler, Formatter
        root = logging.getLogger()
        hdlr = StreamHandler(response)
        fmt = Formatter(logging.BASIC_FORMAT)
        hdlr.setFormatter(fmt)
        root.addHandler(hdlr)
        root.setLevel(10)


    def navlinks(self, devObj, response):
        """add navigation links to the end of the loader output"""
        devurl = devObj.absolute_url()
        response.write("""Review the settings for <a href=%s>%s</a>\n"""
                % (devurl, devObj.getId()))
        response.write(
        """Add another <a href="/zport/dmd/DeviceLoader/addDevice">device</a>\n""")
