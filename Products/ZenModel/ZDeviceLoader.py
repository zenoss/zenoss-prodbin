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
from AccessControl import Permissions as permissions

from OFS.SimpleItem import SimpleItem

from Products.SnmpCollector.SnmpCollector import SnmpCollector

from ZenModelItem import ZenModelItem
from Device import manage_createDevice


def manage_addZDeviceLoader(context, id="", REQUEST = None):
    """make a DeviceLoader"""
    if not id: id = "DeviceLoader"
    d = ZDeviceLoader(id)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 


class ZDeviceLoader(ZenModelItem,SimpleItem):
    """Load devices into the DMD database"""

    portal_type = meta_type = 'DeviceLoader'

    manage_options = ((
            {'label':'ManualDeviceLoader', 'action':'manualDeviceLoader'},
            ) + SimpleItem.manage_options)

   
    security = ClassSecurityInfo()

    factory_type_information = ( 
        { 
            'id'             : 'Device',
            'meta_type'      : 'Device',
            'description'    : """Base class for all devices""",
            'icon'           : 'Device_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addDevice',
            'immediate_view' : 'addDevice',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'addDevice'
                , 'permissions'   : (
                  permissions.view, )
                },
            )
        },
        )

    def __init__(self, id):
        self.id = id


    def __call__(self):
        """addDevice is default screen"""
        self.addDevice()


    def loadDevice(self, deviceName, devicePath="", 
            tag="", serialNumber="",
            snmpCommunity="public", snmpPort=161,
            rackSlot=0, productionState=1000, comments="",
            manufacturer="", model="", 
            locationPath="", rack="",
            groupPaths=[], systemPaths=[],
            statusMonitors=["localhost"], cricketMonitor="localhost",
            REQUEST = None):
        """
        Load a device into the database connecting its major relations
        and collecting its configuration. 
        """
        if not deviceName: return self.callZenScreen(REQUEST)
        device = None
        if REQUEST:
            response = REQUEST.RESPONSE
            dlh = self.deviceLoggingHeader()
            idx = dlh.rindex("</table>")
            response.write(dlh[:idx])
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
            device.collectConfig(wrap=False, REQUEST=REQUEST)
            logging.info("device %s loaded!" % deviceName)
        if REQUEST:
            self.loaderFooter(device, response)
            self.clearLog()


    def addManufacturer(self, newManufacturerName, REQUEST=None):
        """add a manufacturer to the database"""
        self.getDmdRoot("Companies").getCompany(newManufacturerName)
        if REQUEST:
            REQUEST['manufacturer'] = newManufacturerName
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'setModel')
    def setModel(self, manufacturer, newModelName, REQUEST=None):
        """set the model of this device"""
        modelObj = self.getDmdRoot("Products").getModelProduct(
                                        manufacturer, newModelName)
        if REQUEST:
            REQUEST['model'] = newModelName
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'setLocation')
    def addLocation(self, newLocationPath, REQUEST=None):
        """add a location to the database"""
        self.getDmdRoot("Locations").createOrganizer(newLocationPath)
        if REQUEST:
            REQUEST['locationPath'] = newLocationPath
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'addSystem')
    def addSystem(self, newSystemPath, REQUEST=None):
        """add a system to the database"""
        self.getDmdRoot("Systems").createOrganizer(newSystemPath)
        syss = REQUEST.get('systemPaths', [])
        syss.append(newSystemPath)
        if REQUEST:
            REQUEST['systemPaths'] = syss
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'addDeviceGroup')
    def addDeviceGroup(self, newDeviceGroupPath, REQUEST=None):
        """add a device group to the database"""
        self.getDmdRoot("Groups").createOrganizer(newDeviceGroupPath)
        groups = REQUEST.get('groupPaths', [])
        groups.append(newDeviceGroupPath)
        if REQUEST:
            REQUEST['groupPaths'] = groups
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'addStatusMonitor')
    def addStatusMonitor(self, newStatusMonitor, REQUEST=None):
        """add new status monitor to the database"""
        self.getDmdRoot("Monitors").getStatusMonitor(newStatusMonitor)
        mons = REQUEST.get('statusMonitors', [])
        mons.append(newStatusMonitor)
        if REQUEST:
            REQUEST['statusMonitors'] = mons
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'setCricketMonitor')
    def setCricketMonitor(self, newCricketMonitor, REQUEST=None):
        """add new cricket monitor to the database"""
        self.getDmdRoot("Monitors").getCricketMonitor(newCricketMonitor)
        if REQUEST:
            REQUEST['cricketMonitor'] = newCricketMonitor
            return self.callZenScreen(REQUEST)


    def setupLog(self, response):
        """setup logging package to send to browser"""
        from logging import StreamHandler, Formatter
        root = logging.getLogger()
        self._v_handler = StreamHandler(response)
        fmt = Formatter("""<tr class="tablevalues">
        <td>%(asctime)s</td><td>%(levelname)s</td>
        <td>%(name)s</td><td>%(message)s</td></tr>
        """)
        self._v_handler.setFormatter(fmt)
        root.addHandler(self._v_handler)
        root.setLevel(10)


    def clearLog(self):
        log = logging.getLogger()
        if getattr(self, "_v_handler", False):
            log.removeHandler(self._v_handler)


    def loaderFooter(self, devObj, response):
        """add navigation links to the end of the loader output"""
        devurl = devObj.absolute_url()
        response.write("""<tr class="tableheader"><td colspan="4">
            Navigate to device <a href=%s>%s</a></td></tr>""" 
            % (devurl, devObj.getId()))
        response.write("</table></body></html>")
