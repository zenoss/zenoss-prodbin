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

__doc__="""ZDeviceLoader.py

load devices from a GUI screen in the ZMI

$Id: ZDeviceLoader.py,v 1.19 2004/04/22 02:14:12 edahl Exp $"""

__version__ = "$Revision: 1.19 $"[11:-2]

import logging
log = logging.getLogger("zen.DeviceLoader")

import transaction
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions

from OFS.SimpleItem import SimpleItem

from Device import manage_createDevice
from Products.ZenUtils.Utils import setWebLoggingStream, clearWebLoggingStream
from Products.ZenUtils.Exceptions import ZentinelException
from Products.ZenModel.Exceptions import DeviceExistsError, NoSnmp
from ZenModelItem import ZenModelItem


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


    def loadDevice(self, deviceName, devicePath="/Discovered",
            tag="", serialNumber="",
            zSnmpCommunity="", zSnmpPort=161, zSnmpVer=None,
            rackSlot=0, productionState=1000, comments="",
            hwManufacturer="", hwProductName="",
            osManufacturer="", osProductName="",
            locationPath="", groupPaths=[], systemPaths=[],
            statusMonitors=["localhost"], performanceMonitor="localhost",
            discoverProto="snmp",REQUEST = None):
        """
        Load a device into the database connecting its major relations
        and collecting its configuration. 
        """
        xmlrpc = False
        if REQUEST and REQUEST['CONTENT_TYPE'].find('xml') > -1:
            xmlrpc = True
        if zSnmpVer is None:
            try:
                zSnmpVer = str(self.Devices.getOrganizer(devicePath).zSnmpVer)
            except AttributeError:
                zSnmpVer = 'v1'
        if not deviceName: return self.callZenScreen(REQUEST)
        device = None
        if REQUEST and not xmlrpc:
            response = REQUEST.RESPONSE
            dlh = self.deviceLoggingHeader()
            idx = dlh.rindex("</table>")
            dlh = dlh[:idx]
            idx = dlh.rindex("</table>")
            dlh = dlh[:idx]
            response.write(str(dlh[:idx]))
            handler = setWebLoggingStream(response)
        try:
            device = manage_createDevice(self, deviceName, devicePath,
                tag, serialNumber,
                zSnmpCommunity, zSnmpPort, zSnmpVer,
                rackSlot, productionState, comments,
                hwManufacturer, hwProductName,
                osManufacturer, osProductName,
                locationPath, groupPaths, systemPaths,
                statusMonitors, performanceMonitor, discoverProto)
            transaction.commit()
        except (SystemExit, KeyboardInterrupt): raise
        except DeviceExistsError:
            if xmlrpc: return 2
        except NoSnmp:
            if xmlrpc: return 3
        except ZentinelException, e:
            if xmlrpc: return 1
            log.critical(e)
        except:
            log.exception('load of device %s failed' % deviceName)
            transaction.abort()
        else:
            if discoverProto != "none":
                device.collectDevice(setlog=False, REQUEST=REQUEST)
            log.info("device %s loaded!" % deviceName)
        if REQUEST and not xmlrpc:
            self.loaderFooter(device, response)
            clearWebLoggingStream(handler)
        if xmlrpc: return 0


    def addManufacturer(self, newHWManufacturerName=None,
                        newSWManufacturerName=None, REQUEST=None):
        """add a manufacturer to the database"""
        mname = newHWManufacturerName
        field = 'hwManufacturer'
        if not mname:
            mname = newSWManufacturerName
            field = 'osManufacturer'
        self.getDmdRoot("Manufacturers").createManufacturer(mname)
        if REQUEST:
            REQUEST[field] = mname
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'setHWProduct')
    def setHWProduct(self, newHWProductName, hwManufacturer, REQUEST=None):
        """set the productName of this device"""
        self.getDmdRoot("Manufacturers").createHardwareProduct(
                                        newHWProductName, hwManufacturer)
        if REQUEST:
            REQUEST['hwProductName'] = newHWProductName
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'setOSProduct')
    def setOSProduct(self, newOSProductName, osManufacturer, REQUEST=None):
        """set the productName of this device"""
        self.getDmdRoot("Manufacturers").createSoftwareProduct(
                                        newOSProductName, osManufacturer, isOS=True)
        if REQUEST:
            REQUEST['osProductName'] = newOSProductName
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'addLocation')
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


    security.declareProtected('Change Device', 'setPerformanceMonitor')
    def setPerformanceMonitor(self, newPerformanceMonitor, REQUEST=None):
        """add new performance monitor to the database"""
        self.getDmdRoot("Monitors").getPerformanceMonitor(newPerformanceMonitor)
        if REQUEST:
            REQUEST['performanceMonitor'] = newPerformanceMonitor
            return self.callZenScreen(REQUEST)


    def setupLog(self, response):
        """setup logging package to send to browser"""
        from logging import StreamHandler, Formatter
        root = logging.getLogger()
        self._v_handler = StreamHandler(response)
        fmt = Formatter("""<tr class="tablevalues">
        <td>%(asctime)s</td><td>%(levelname)s</td>
        <td>%(name)s</td><td>%(message)s</td></tr>
        """, "%Y-%m-%d %H:%M:%S")
        self._v_handler.setFormatter(fmt)
        root.addHandler(self._v_handler)
        root.setLevel(10)


    def clearLog(self):
        log = logging.getLogger()
        if getattr(self, "_v_handler", False):
            log.removeHandler(self._v_handler)


    def loaderFooter(self, devObj, response):
        """add navigation links to the end of the loader output"""
        if not devObj: return
        devurl = devObj.absolute_url()
        response.write("""<tr class="tableheader"><td colspan="4">
            Navigate to device <a href=%s>%s</a></td></tr>""" 
            % (devurl, devObj.getId()))
        response.write("</table></body></html>")
