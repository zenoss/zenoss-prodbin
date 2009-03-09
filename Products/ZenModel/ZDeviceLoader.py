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

import socket
from logging import StreamHandler, Formatter, getLogger
log = getLogger("zen.DeviceLoader")

import transaction
from zope.interface import implements
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions

from OFS.SimpleItem import SimpleItem

from Products.ZenUtils.Utils import isXmlRpc, setupLoggingHeader 
from Products.ZenUtils.Utils import binPath, clearWebLoggingStream
from Products.ZenUtils.Exceptions import ZentinelException
from Products.ZenModel.Exceptions import DeviceExistsError, NoSnmp
from Products.ZenModel.Device import manage_createDevice
from Products.ZenWidgets import messaging
from Products.Jobber.interfaces import IJobStatus
from Products.Jobber.jobs import ShellCommandJob
from Products.Jobber.status import SUCCESS, FAILURE
from ZenModelItem import ZenModelItem
from zExceptions import BadRequest
from Products.ZenModel.interfaces import IDeviceLoader


def manage_addZDeviceLoader(context, id="", REQUEST = None):
    """make a DeviceLoader"""
    if not id: id = "DeviceLoader"
    d = ZDeviceLoader(id)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main')

class BaseDeviceLoader(object):
    implements(IDeviceLoader)

    context = None
    request = None
    deviceobj = None

    def __init__(self, context):
        self.context = context

    def _set_zProperties(self, zProperties):
        """
        Set zProperties on the device object intelligently. 
        
        If the new value is different from the inherited value, override on
        this device. Otherwise, do nothing, so the inheritance remains.
        """
        if self.deviceobj is not None:
            for prop, newvalue in zProperties.iteritems():
                inherited = getattr(self.deviceobj, prop)
                if newvalue != inherited:
                    self.deviceobj.setZenProperty(prop, newvalue)


    def run_zendisc(self, deviceName, devicePath, performanceMonitor):
        """
        Various ways of doing this should be implemented in subclasses.
        """
        raise NotImplementedError

    def cleanup(self):
        """
        Delete the device object, presumably because discovery failed.
        """
        if self.deviceobj is not None:
            self.deviceobj._p_jar.sync()
            if self.deviceobj.isTempDevice(): 
                # Flag's still True, so discovery failed somehow.  Clean up the
                # device object.
                self.deviceobj.deleteDevice(True, True, True)
                self.deviceobj = None

    def load_device(self, deviceName, devicePath='/Discovered', 
                    discoverProto='snmp', performanceMonitor='localhost',
                    manageIp=None, zProperties=None, deviceProperties=None):
        """
        Load a single device into the database.
        """
        # Make the config dictionaries the proper type
        try:
            if zProperties is None:
                zProperties = {}
            if deviceProperties is None:
                deviceProperties = {}

            # Remove spaces from the name
            deviceName = deviceName.replace(' ', '')

            # If we're not discovering and we have no IP, attempt the IP lookup
            # locally
            if discoverProto=='none':
                if not manageIp:
                    try:
                        manageIp = socket.gethostbyname(deviceName)
                    except socket.error:
                        pass

            # move the zProperties required by manage_createDevice to
            # deviceProperties
            for key in 'zSnmpCommunity', 'zSnmpPort', 'zSnmpVer':
                if zProperties.has_key(key):
                    deviceProperties[key] = zProperties.pop(key)
            
            # Make a device object in the database
            self.deviceobj = manage_createDevice(self.context, deviceName,
                                 devicePath,
                                 performanceMonitor=performanceMonitor,
                                 **deviceProperties)

            # Set zProperties on the device 
            self._set_zProperties(zProperties)

            # Flag this device as temporary. If discovery goes well, zendisc will
            # flip this to False.
            self.deviceobj._temp_device = True

            # Commit to database so everybody can find the new device
            transaction.commit()

            # If we're not discovering, we're done
            if discoverProto=='none':
                return self.deviceobj

            # Otherwise, time for zendisc to do its thing
            self.run_zendisc(deviceName, devicePath, performanceMonitor)

        finally:
            # Check discovery's success and clean up accordingly
            self.cleanup()

        return self.deviceobj


class JobDeviceLoader(BaseDeviceLoader):
    implements(IDeviceLoader)

    def run_zendisc(self, deviceName, devicePath, performanceMonitor):
        """
        In this subclass, just create the zendisc command and return it. The
        job will do the actual running.
        """
        zm = binPath('zendisc')
        zendiscCmd = [zm]
        zendiscOptions = ['run', '--now','-d', deviceName,
                     '--monitor', performanceMonitor, 
                     '--deviceclass', devicePath]
        zendiscCmd.extend(zendiscOptions)
        self.zendiscCmd = zendiscCmd

    def cleanup(self):
        """
        Delegate cleanup to the Job itself.
        """
        pass


class DeviceCreationJob(ShellCommandJob):
    def __init__(self, jobid, deviceName, devicePath="/Discovered", tag="",
                 serialNumber="", rackSlot=0, productionState=1000,
                 comments="", hwManufacturer="", hwProductName="",
                 osManufacturer="", osProductName="", locationPath="",
                 groupPaths=[], systemPaths=[], performanceMonitor="localhost",
                 discoverProto="snmp", priority=3, manageIp="",
                 zProperties=None):

        # Store device name for later finding
        self.deviceName = deviceName
        self.devicePath = devicePath
        self.performanceMonitor = performanceMonitor
        self.discoverProto = discoverProto
        self.manageIp = manageIp

        # Save the device stuff to set after adding
        self.zProperties = zProperties
        self.deviceProps = dict(tag=tag,
                          serialNumber=serialNumber,
                          rackSlot=rackSlot,
                          productionState=productionState,
                          comments=comments,
                          hwManufacturer=hwManufacturer,
                          hwProductName = hwProductName,
                          osManufacturer = osManufacturer,
                          osProductName = osProductName,
                          locationPath = locationPath,
                          groupPaths = groupPaths,
                          systemPaths = systemPaths,
                          priority = priority)

        # Set up the job, passing in a blank command (gets set later)
        super(DeviceCreationJob, self).__init__(jobid, '')

    def run(self, r):
        self._v_loader = JobDeviceLoader(self)
        # Create the device object and generate the zendisc command
        try:
            self._v_loader.load_device(self.deviceName, self.devicePath,
                                    self.discoverProto,
                                    self.performanceMonitor, self.manageIp,
                                    self.zProperties, self.deviceProps)
        except Exception, e:
            transaction.commit()
            log = self.getStatus().getLog()
            log.write(e.args[0])
            log.finish()
            self.finished(FAILURE)
        else:
            self.cmd = self._v_loader.zendiscCmd
            super(DeviceCreationJob, self).run(r)

    def finished(self, r):
        self._v_loader.cleanup()
        if self._v_loader.deviceobj is not None and r!=FAILURE:
            # Discovery succeeded. Really set those properties good.
            self.postDeviceAdd()
            result = SUCCESS
        else:
            result = FAILURE
        super(DeviceCreationJob, self).finished(result)

    def postDeviceAdd(self):
        """
        Set the properties on the device after it's been added.
        """
        self._p_jar.sync()
        dev = self._v_loader.deviceobj
        props = self.deviceProps
        # Set up the hw/os props correctly
        props['hwManufacturer'] = props['hwManufacturer'] or \
            dev.hw.getManufacturerName()
        props['hwProductName'] = props['hwProductName'] or \
            dev.hw.getProductName()
        props['osManufacturer'] = props['osManufacturer'] or \
            dev.os.getManufacturerName()
        props['osProductName'] = props['osProductName'] or \
            dev.os.getProductName()

        # Store the props on the device
        dev.manage_editDevice(**props)


class WeblogDeviceLoader(BaseDeviceLoader):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def run_zendisc(self, deviceName, devicePath, performanceMonitor):
        collector = self.deviceobj.getPerformanceServer()
        collector._executeZenDiscCommand(deviceName, devicePath,
                                         performanceMonitor,
                                         REQUEST=self.request)


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
            performanceMonitor="localhost",
            discoverProto="snmp",priority=3,REQUEST=None):
        """
        Load a device into the database connecting its major relations
        and collecting its configuration.
        """
        device = None
        if not deviceName: return self.callZenScreen(REQUEST)
        xmlrpc = isXmlRpc(REQUEST)
        if REQUEST and not xmlrpc:
            handler = setupLoggingHeader(self, REQUEST)

        loader = WeblogDeviceLoader(self, REQUEST)

        try:
            device = loader.load_device(deviceName, devicePath, discoverProto,
                                        performanceMonitor,
                                        zProperties=dict(
                                            zSnmpCommunity=zSnmpCommunity,
                                            zSnmpPort=zSnmpPort,
                                            zSnmpVer=zSnmpVer
                                        ),
                                        deviceProperties=dict(
                                            tag=tag,
                                            serialNumber=serialNumber,
                                            rackSlot=rackSlot,
                                            productionState=productionState,
                                            comments=comments,
                                            hwManufacturer=hwManufacturer,
                                            hwProductName=hwProductName,
                                            osManufacturer=osManufacturer,
                                            osProductName=osProductName,
                                            locationPath=locationPath,
                                            groupPaths=groupPaths,
                                            systemPaths=systemPaths,
                                            priority=priority
                                        ))
        except (SystemExit, KeyboardInterrupt): 
            raise
        except ZentinelException, e:
            log.info(e)
            if xmlrpc: return 1
        except DeviceExistsError, e:
            log.info(e)
            if xmlrpc: return 2
        except NoSnmp, e:
            log.info(e)
            if xmlrpc: return 3
        except Exception, e:
            log.exception(e)
            log.exception('load of device %s failed' % deviceName)
            transaction.abort()
        if device is None:
            log.error("Unable to add the device %s" % deviceName)
        else:
            log.info("Device %s loaded!" % deviceName)

        if REQUEST and not xmlrpc:
            self.loaderFooter(device, REQUEST.RESPONSE)
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
        try:
            self.getDmdRoot("Manufacturers").createManufacturer(mname)
        except BadRequest, e:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    str(e),
                    priority=messaging.WARNING
                )
            else:
                raise e

        if REQUEST:
            REQUEST[field] = mname
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'setHWProduct')
    def setHWProduct(self, newHWProductName, hwManufacturer, REQUEST=None):
        """set the productName of this device"""
        if not hwManufacturer and REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Error',
                'Please select a HW Manufacturer',
                priority=messaging.WARNING
            )
            return self.callZenScreen(REQUEST) 

        self.getDmdRoot("Manufacturers").createHardwareProduct(
                                        newHWProductName, hwManufacturer)
        if REQUEST:
            REQUEST['hwProductName'] = newHWProductName
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'setOSProduct')
    def setOSProduct(self, newOSProductName, osManufacturer, REQUEST=None):
        """set the productName of this device"""
        if not osManufacturer and REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Error',
                'Please select an OS Manufacturer.',
                priority=messaging.WARNING
            )
            return self.callZenScreen(REQUEST)

        self.getDmdRoot("Manufacturers").createSoftwareProduct(
                                        newOSProductName, osManufacturer, isOS=True)
        if REQUEST:
            REQUEST['osProductName'] = newOSProductName
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'addLocation')
    def addLocation(self, newLocationPath, REQUEST=None):
        """add a location to the database"""
        try:
            self.getDmdRoot("Locations").createOrganizer(newLocationPath)
        except BadRequest, e:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    str(e),
                    priority=messaging.WARNING
                )
            else: 
                raise e
            
        if REQUEST:
            REQUEST['locationPath'] = newLocationPath
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'addSystem')
    def addSystem(self, newSystemPath, REQUEST=None):
        """add a system to the database"""
        try:
            self.getDmdRoot("Systems").createOrganizer(newSystemPath)
        except BadRequest, e:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    str(e),
                    priority=messaging.WARNING
                )
            else: 
                raise e

        syss = REQUEST.get('systemPaths', [])
        syss.append(newSystemPath)
        if REQUEST:
            REQUEST['systemPaths'] = syss
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'addDeviceGroup')
    def addDeviceGroup(self, newDeviceGroupPath, REQUEST=None):
        """add a device group to the database"""
        try:
            self.getDmdRoot("Groups").createOrganizer(newDeviceGroupPath)
        except BadRequest, e:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    str(e),
                    priority=messaging.WARNING
                )
            else: 
                raise e

        groups = REQUEST.get('groupPaths', [])
        groups.append(newDeviceGroupPath)
        if REQUEST:
            REQUEST['groupPaths'] = groups
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'setPerformanceMonitor')
    def setPerformanceMonitor(self, newPerformanceMonitor, REQUEST=None):
        """add new performance monitor to the database"""
        try:
            self.getDmdRoot("Monitors").getPerformanceMonitor(newPerformanceMonitor)
        except BadRequest, e:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    str(e),
                    priority=messaging.WARNING
                )
            else: 
                raise e 
        if REQUEST:
            REQUEST['performanceMonitor'] = newPerformanceMonitor
            return self.callZenScreen(REQUEST)


    def setupLog(self, response):
        """setup logging package to send to browser"""
        root = getLogger()
        self._v_handler = StreamHandler(response)
        fmt = Formatter("""<tr class="tablevalues">
        <td>%(asctime)s</td><td>%(levelname)s</td>
        <td>%(name)s</td><td>%(message)s</td></tr>
        """, "%Y-%m-%d %H:%M:%S")
        self._v_handler.setFormatter(fmt)
        root.addHandler(self._v_handler)
        root.setLevel(10)


    def clearLog(self):
        alog = getLogger()
        if getattr(self, "_v_handler", False):
            alog.removeHandler(self._v_handler)


    def loaderFooter(self, devObj, response):
        """add navigation links to the end of the loader output"""
        if not devObj: return
        devurl = devObj.absolute_url()
        response.write("""<tr class="tableheader"><td colspan="4">
            Navigate to device <a href=%s>%s</a></td></tr>""" 
            % (devurl, devObj.getId()))
        response.write("</table></body></html>")
