#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""BasicDeviceLoader.py

BasicDeviceLoader.py populates the dmd with devices from a file.  The input file
only needs to have a list of machines.  It uses the Classifier system
to figure out where in the DeviceClass a new device should be created.
If no location is found it will use a specified default path or put
the device in the top level of the DevicesClass tree.

$Id: BasicDeviceLoader.py,v 1.19 2004/04/04 01:51:19 edahl Exp $"""

__version__ = "$Revision: 1.19 $"[11:-2]

from logging import debug, info, warn, critical, exception

from Products.ZenModel.Exceptions import *


class BasicDeviceLoader:
    '''Load a machine'''

    def loadDevice(self, deviceName, devicePath="", systemPath="",
                manufacturer="", model="", groupPath="", 
                locationPath="", rack="",
                statusMonitorName="localhost", cricketMonitorName="localhost",
                snmpCommunity="", snmpPort=None,
                loginName="", loginPassword=""):
        """load a device into the database"""
        info("adding device %s" % deviceName)
        device = self.getDevice(deviceName, devicePath, snmpCommunity, snmpPort,
                            loginName, loginPassword)

        if manufacturer and model:
            info("setting manufacturer to %s model to %s"
                            % (manufacturer, model))
            device.setModel(manufacturer, model)

        if not locationPath: locationPath = self.getLocationPath()
        if locationPath: 
            if rack:
                locationPath += "/%s" % rack
                info("setting rack location to %s" % locationPath)
                device.setRackLocation(locationPath)
            else:
                info("setting location to %s" % locationPath)
                device.setLocation(locationPath)

        if not groupPath: groupPath = self.getGroupPath()
        if groupPath: 
            info("setting group %s" % groupPath)
            device.setGroups(groupPath)

        if not systemPath: systemPath = self.getSystemPath()
        if systemPath: 
            info("setting system %s" % systemPath)
            device.setSystems(systemPath)

        if not statusMonitorName: 
            statusMonitorName = self.getStatusMonitorName()
        info("setting status monitor to %s" % statusMonitorName)
        device.setStatusMonitor(statusMonitorName)

        if not cricketMonitorName:
            cricketMonitorName = self.getCricketMonitorName()
        info("setting cricket monitor to %s" % cricketMonitorName)
        device.setCricketMonitor(cricketMonitorName)
       
        return device

    
    def getDevice(self, deviceName, devicePath, 
                snmpCommunity, snmpPort, loginName, loginPassword):
        """get a device if devicePath is None try classifier"""
        self.classificationEntry = None
        if self.getDmdRoot("Devices").findDevice(deviceName):
            raise DeviceExistsError, "Device %s already exists" % deviceName
        if not devicePath:
            self.classificationEntry = \
                self.getDmdRoot("Devices").ZenClassifier.classifyDevice(
                                        deviceName,
                                        snmpCommunity, snmpPort,
                                        loginName, loginPassword)
            if not self.classificationEntry: 
                raise DeviceNotClassified, \
                    "classifier failed to classify device %s" % deviceName
            devicePath = self.classificationEntry.getDeviceClassPath

        deviceClass = self.getDmdRoot("Devices").getOrganizer(devicePath)
        if not deviceClass:
            raise PathNotFoundError, \
                "Path to device %s is not valid" % deviceName
        return deviceClass.createInstance(deviceName)


    def getLocationPath(self):
        """get the location path for an object"""
        pass


    def getGroupPath(self):
        """override if you need to derive the group name from something else"""
        pass


    def getSystemPath(self):
        """override if you need to derive the system name from something else"""
        pass
       

    def getStatusMonitorName(self):
        """return the status monitor name, default is localhost"""
        return "localhost"
      

    def getCricketMonitorName(self):
        """return the cricket monitor name, default is localhost"""
        return "localhost"


if __name__ == "__main__":
    loader = BasicDeviceLoader()
    loader.loadDatabase()
    print "Database Load is finished!"
