##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """zenbatchdump

zenbatchdump dumps a list of devices to a file.
"""

import sys
import re
from datetime import datetime
import platform
from collections import defaultdict

import Globals

from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.Device import Device
from Products.ZenModel.DeviceOrganizer import DeviceOrganizer


class BatchDeviceDumper(ZCmdBase):
    """
    Base class
    """

    sample_configs = """#
# zenbatchdump run on host zenoss41 on date 2011-10-16 16:34:23.569920
# with --root=Devices/Server/Linux
# To load this Device dump file, use:
#   zenbatchload <file>


'/Locations'
'/Locations/TestZenBatchDumper'
'/Locations/TestZenBatchDumper/City1'
'/Locations/TestZenBatchDumper/City1/Building1'
'/Locations/TestZenBatchDumper/City2'


'/Systems'
'/Systems/TestZenBatchDumper'
'/Systems/TestZenBatchDumper/System1'
'/Systems/TestZenBatchDumper/Scary/System2'
'/Systems/TestZenBatchDumper/Scary/System3'


'/Groups'
'/Groups/TestZenBatchDumper'
'/Groups/TestZenBatchDumper/Production'
'/Groups/TestZenBatchDumper/Production/Critical'
'/Groups/TestZenBatchDumper/Production/Secondary'
'/Groups/TestZenBatchDumper/TEST'
'/Groups/TestZenBatchDumper/DEV'

'/Devices/TestZenBatchDumper'  zCollectorPlugins=['zenoss.snmp.NewDeviceMap', 'zenoss.snmp.DeviceMap', 'HPDeviceMap', 'DellDeviceMap', 'zenoss.snmp.InterfaceMap', 'zenoss.snmp.RouteMap', 'zenoss.snmp.IpServiceMap', 'zenoss.snmp.HRFileSystemMap', 'zenoss.snmp.HRSWInstalledMap', 'zenoss.snmp.HRSWRunMap', 'zenoss.snmp.CpuMap', 'HPCPUMap', 'DellCPUMap', 'DellPCIMap'], zIcon='/zport/dmd/img/icons/server.png'

'/Devices/TestZenBatchDumper/Server'  zCollectorPlugins=['zenoss.snmp.NewDeviceMap', 'zenoss.snmp.DeviceMap', 'HPDeviceMap', 'DellDeviceMap', 'zenoss.snmp.InterfaceMap', 'zenoss.snmp.RouteMap', 'zenoss.snmp.IpServiceMap', 'zenoss.snmp.HRFileSystemMap', 'zenoss.snmp.HRSWInstalledMap', 'zenoss.snmp.HRSWRunMap', 'zenoss.snmp.CpuMap', 'HPCPUMap', 'DellCPUMap', 'DellPCIMap'], zIcon='/zport/dmd/img/icons/server.png'

'/Devices/TestZenBatchDumper/Server/Linux'  zCollectorPlugins=['zenoss.snmp.NewDeviceMap', 'zenoss.snmp.DeviceMap', 'HPDeviceMap', 'DellDeviceMap', 'zenoss.snmp.InterfaceMap', 'zenoss.snmp.RouteMap', 'zenoss.snmp.IpServiceMap', 'zenoss.snmp.HRFileSystemMap', 'zenoss.snmp.HRSWRunMap', 'zenoss.snmp.CpuMap', 'HPCPUMap', 'DellCPUMap', 'DellPCIMap'], zHardDiskMapMatch='^[hs]d[a-z]\\d+$|c\\d+t\\d+d\\d+s\\d+$|^cciss\\/c\\dd\\dp\\d$|^dm\\-\\d$', zIcon='/zport/dmd/img/icons/server-linux.png', zIpServiceMapMaxPort=8090

'localhost' setHWProductKey=('.1.3.6.1.4.1.8072.3.2.10', 'net snmp'), setHWSerialNumber='', setHWTag='', setLastChange=DateTime('2011/10/16 09:07:53.208444 GMT-7'), setManageIp='127.0.0.1', setOSProductKey='Linux 2.6.18-164.el5', setPriority=3, setProdState=1000, setPerformanceMonitor='localhost'

'thor' setLocation='/Locations/TestZenBatchDumper/City1', setSystems=['/Systems/TestZenBatchDumper/Scary/System2', '/Systems/TestZenBatchDumper/System1'], setGroups=['/Groups/TestZenBatchDumper/TEST', '/Groups/TestZenBatchDumper/DEV'], setHWProductKey=('.1.3.6.1.4.1.8072.3.2.10', 'net snmp'), setHWSerialNumber='', setHWTag='', setLastChange=DateTime('2011/10/16 09:22:59.450108 GMT-7'), setManageIp='192.168.55.225', setOSProductKey='Linux 2.6.32-25-server', setPriority=4, setProdState=1000, setPerformanceMonitor='localhost'

'loki' setLocation='/Locations/TestZenBatchDumper/City2', setSystems=['/Systems/TestZenBatchDumper/System1'], setGroups=['/Groups/TestZenBatchDumper/Production/Critical'], setHWProductKey=('.1.3.6.1.4.1.8072.3.2.10', 'net snmp'), setHWSerialNumber='', setHWTag='', setLastChange=DateTime('2011/10/16 09:19:59.450108 GMT-7'), setManageIp='192.168.55.223', setOSProductKey='Linux 2.6.32-25-server', setPriority=4, setProdState=1000, setPerformanceMonitor='localhost'

'/Devices/TestZenBatchDumper/Server/Windows'  zCollectorPlugins=['zenoss.snmp.NewDeviceMap', 'zenoss.snmp.DeviceMap', 'HPDeviceMap', 'DellDeviceMap', 'zenoss.snmp.InterfaceMap', 'zenoss.snmp.RouteMap', 'zenoss.snmp.IpServiceMap', 'zenoss.snmp.HRFileSystemMap', 'zenoss.snmp.HRSWInstalledMap', 'zenoss.snmp.HRSWRunMap', 'zenoss.snmp.CpuMap', 'HPCPUMap', 'DellCPUMap', 'DellPCIMap', 'zenoss.snmp.InformantHardDiskMap', 'zenoss.wmi.WinServiceMap'], zHardDiskMapMatch='.*', zIcon='/zport/dmd/img/icons/server-windows.png', zWinEventlog=True, zWmiMonitorIgnore=False

'/Devices/TestZenBatchDumper/Server/Windows/WMI'  zCollectorPlugins=['zenoss.wmi.WindowsDeviceMap', 'zenoss.wmi.WinServiceMap', 'zenoss.wmi.CpuMap', 'zenoss.wmi.FileSystemMap', 'zenoss.wmi.IpInterfaceMap', 'zenoss.wmi.IpRouteMap', 'zenoss.wmi.MemoryMap', 'zenoss.wmi.ProcessMap', 'zenoss.wmi.SoftwareMap'], zDeviceTemplates=['Device_WMI'], zWinPerfCycleSeconds=300, zWinPerfCyclesPerConnection=10

'192.168.5.219' zWinPassword='easyPassword', zWinUser='admin', setLocation='/Locations/TestZenBatchDumper/City1/Building1', setGroups=['/Groups/TestZenBatchDumper/Production/Secondary'], setHWProductKey=('Unknown', 'Chassis Manufacture'), setHWSerialNumber='Chassis Serial Number', setHWTag='Asset-1234567890', setLastChange=DateTime('2011/10/16 09:19:56.920976 GMT-7'), setManageIp='192.168.55.229', setOSProductKey=('Windows 7 Home Premium ', 'Microsoft'), setPriority=3, setProdState=1000, setPerformanceMonitor='localhost'


# Dumped:
#            Locations: 5
#               Groups: 7
#              Systems: 5
#        DeviceClasses: 5
#              Devices: 4
"""
    # Export out the following setter method data
    ignoreSetters = (
        'setLastPollSnmpUpTime', 'setSnmpLastCollection',
        'setSiteManager', 'setLocation', 'setGroups', 'setSystems',
    )

    def __init__(self, *args, **kwargs):
        ZCmdBase.__init__(self, *args, **kwargs)
        self.defaults = {}
        self.emittedDeviceClasses = set()

    def _prepRoot(self):
        """
        initializes and verify the device root and prune options properly
 
        @return: was initialization successful
        @rtype: bool
        """

        if self.options.root == "":
            self.root = self.dmd.Devices
            self.options.prune = False
        else:
            try:
                self.root = self.dmd.unrestrictedTraverse(self.options.root)
            except KeyError:
                self.log.error("%s is not a valid DeviceOrganizer path under %s\n",
                               self.options.root, self.dmd.getPrimaryUrlPath())
                return False

        self.rootPath = self.root.getPrimaryUrlPath()
        return True

    def _emitProps(self, obj):
        """
        Returns string of object local zProperties, cProperties and "setter"
        properties suitable for ZenBatchLoader

        @parameter obj: a Device or DeviceClass (or perhaps Location later)
        @type obj: ZenModelRM
        @return: string containing local zProperties as documented in above sample
        @rtype str
        """
        props = []

        # description has neither setter nor getter so we special-case it here
        desc = getattr(obj, "description", "")
        if desc:
            props.append("%s=%s" % ('description', repr(desc)))

        # Z-properties
        for prop in ((x['id'], repr(x['value'])) for x in obj.exportZProperties() \
                           if self.isPropExportable(x)):
            key = prop[0]
            if obj.zenPropIsPassword(key):
                val = repr(getattr(obj, key, ''))
                prop = (key, val)
            props.append("%s=%s" % prop)

        # C-properties
        for cProp in obj.custPropertyMap():
            if cProp['id'] == 'cDateTest': continue
            value = getattr(obj,cProp['id'],'')
            if value and value != '':
                props.append("%s=%s" % (cProp['id'], repr(value)))

        for setMethod in [setter for setter in dir(obj) if setter.startswith('set')]:
            if setMethod in self.ignoreSetters:
                continue
            getMethod = setMethod.replace('set', 'get', 1)
            getter = getattr(obj, getMethod, None)
            if getter and callable(getter):
                # Deal with brain damaged get/setProdState
                if setMethod == 'setProdState':
                    states = obj.getProdStateConversions()
                    for state in states:
                        if getter() in state:
                            value = state[1]
                else:
                    value = getter()
                if value and value != '':
                    props.append("%s=%s" % (setMethod, repr(value)))
            else:
                # for setters that have no getter, try a bare attribute
                value = getattr(obj, setMethod[3:].lower(), None)
                if value and value != '':
                    props.append("%s=%s" % (setMethod, repr(value)))

        # There's always got to be a weirdie....
        if ('getPerformanceServerName' in dir(obj)):
            props.append("setPerformanceMonitor=" + repr(obj.getPerformanceServerName()))
        return sorted(props)

    def isPropExportable(self, propdict):
        """
        Dump the specified property to the output file?
        propdict contents:
             id - name of the zprop
             category - as displayed in the 'Configuration Property' area
             islocal - overridden here?
             value - raw value
             options - complete list of items that can be chosen
             valueAsString - value in string format
             path - path of where the zprop was defined
             type - 'password', 'string', 'int', 'float', 'date', 'lines'

        """
        return propdict['islocal']

    def _emitDev(self, dev):
        """
        Returns a device and its zProperties in strings appropriate for ZenBatchLoader
       
        @parameter dev: Device object to emit
        @type dev: Device
        @return: device name and list of Device-local zProperties and cProperties
        @rtype: tuple of strings
        """

        result = self._emitProps(dev)

        location = dev.location()
        if location:
            result.append("setLocation=" + repr("/".join(location.getPrimaryPath()[4:])))

        systems = self._normalizePaths(dev.systems())
        if systems:
            result.append("setSystems=" + repr(systems))

        groups = self._normalizePaths(dev.groups())
        if groups:
            result.append("setGroups=" + repr(groups))

        if self.options.noorganizers:
            # Need to be able to tell which device class we came from
            result.append("moveDevices=('%s', '%s')" % (
                          '/'.join(dev.getPrimaryPath()[:-2]), dev.id))

        return (repr(dev.getId()), sorted(result))

    def _normalizePaths(self, objList):
        """
        Given a list of objects, make their URL path representation
        look closer to what is seen in 'Infrastructure' view.
        """
        return sorted('/' + '/'.join(obj.getPrimaryPath()[4:]) for obj in objList)

    def _emitOrg(self, org):
        """
        Returns a device organizer with its type and local properties

        @parameter org: DeviceOrganizer to emit
        @type org: DeviceOrganizer
        @return: device organizer name, type and properties
        @rtype: tuple of strings
        """

        path = org.getPrimaryPath()
        name = "'/%s' " % "/".join(path[3:])
        # Avoid things that override base classes for the moment (eg uses zPythonClass)
        props = []
        if not (isinstance(org, DeviceClass) and 'ZenPacks' in org.zPythonClass):
            props = self._emitProps(org)

        if '/Locations/' in path:
            props.append('setAddress="%s"' % org.address)

        return (name, props)

    def _backtraceOrg(self, outFile, obj):
        """
        Recurse upward from a device emitting parent DeviceClasses if not already emitted
       
        @parameter outFile: file object to which output is written
        @type outFile: file or other object with .write() method that is simillar
        @parameter dev: Device/DeviceClass for whom we emit parent Organizer paths
        @type dev: Device or DeviceClass
        @return: number of DeviceClasses emitted
        @rtype: int
        """

        result = 0
        if isinstance(obj, Device):
            # back out to first containing DeviceOrganizer
            obj = obj.getPrimaryParent().getPrimaryParent()

        if not obj in self.emittedDeviceClasses:
            parent = obj.getPrimaryParent()
            # don't recurse to dmd
            if parent.getPrimaryPath()[2:] != self.dmd.getPrimaryPath()[2:]:
                result = self._backtraceOrg(outFile, parent)
            (name, props) = self._emitOrg(obj);
            outFile.write("\n%s %s\n" % (name, ", ".join(props)))
            self.emittedDeviceClasses.add(obj)
            result += 1
        return result
 
    def listLSGOTree(self, outFile, branch):
        """
        Recurse through the Locations, Systems and Groups trees
        printing out Organizers with properties

        @parameter outFile: output object to which we write output
        @type outFile: file or other object with .write() method that is simillar
        @parameter branch: object reference to current tree branch
        @type branch: DeviceOrganizer
        @return: number of Locations, Systems or Groups dumped
        @rtype: int
        """
        if getattr(self.options, 'rootPath', None) is None:
            # BatchDeviceDumper.run() already calls ._prepRoot() before
            # we get here, but leaving this in
            # for unit tests and unexpected uses
            if not self._prepRoot():
                return -1;

        result = 0

        if not isinstance(branch, DeviceOrganizer):
            raise TypeError("listLSGOTree must start in a DeviceOrganizer not (%s)" % branch)

        # Hidden option for pruning LSG Organizers as pruned 
        # ones may get referenced by unpruned devices
        # This is to be used by unit tests to simplify output
        if getattr(self.options, 'pruneLSGO', None) and \
           not isinstance(self.root, DeviceClass) and \
           not (branch.getPrimaryUrlPath().startswith(self.rootPath) or \
                self.root.getPrimaryUrlPath().startswith(branch.getPrimaryUrlPath())):
            return result

        outFile.write("\n")
        (name, props) = self._emitOrg(branch)
        result += 1
        outFile.write("\n%s %s\n" % (name, ", ".join(props)))
        
        for org in branch.children():
           result += self.listLSGOTree(outFile, org)
        return result

    def makeRegexMatcher(self):
        regex = re.compile(self.options.regex)
        return lambda dev: dev is not None and regex.match(dev.id)

    def chooseDevice(self, root, matcher=None):
        for dev in root.getDevices():
            # can likely remove this next line, as I only call this from within the dmd.Devices tree
            # was here for when I could be traversing the LSGOrganizers and finding devices there
            dev = self.dmd.unrestrictedTraverse(dev.getPrimaryPath())
            if not dev in self.root.getSubDevices():
                continue
            if 'ZenPack' in dev.zPythonClass:
                continue
            if matcher:
                if matcher(dev):
                    yield dev
            else:
                yield dev

    def listDeviceTree(self, outFile, branch=None):
        """
        Recurse through the Devices tree printing out Organizers and
        Devices with properties
        return number of Devices emitted

        @parameter outFile: output object to which we write output
        @type outFile: file or other object with .write() method that is simillar
        @parameter branch: object reference to current tree branch
        @type branch: DeviceClass (or perhaps DeviceOrganizer at worst)
        @return: number of leaf Devices and DeviceClasses dumped
        @rtype: dict
        """
        if getattr(self.options, 'rootPath', None) is None:
            # BatchDeviceDumper.run() already calls ._prepRoot()
            # before we get here, but leaving this in
            # for unit tests and unexpected uses
            if not self._prepRoot():
                return { 'fail' : True }

        if branch is None:
            branch = self.dmd.Devices

        if not isinstance(branch, DeviceClass):
            raise TypeError("listDeviceTree must start in a DeviceClass not " + repr(branch))

        result = defaultdict(int)

        # Dump DeviceClass if not pruned
        if not self.options.prune or branch.getPrimaryUrlPath() in self.rootPath:
            if not self.options.noorganizers:
                outFile.write("\n")
                (name, props) = self._emitOrg(branch)
                result['DeviceClasses'] += 1
                outFile.write("\n%s %s\n" % (name, ", ".join(props)))
                self.emittedDeviceClasses.add(branch)

        # Dump all eligible Devices in this DeviceClass (pruning occurs in .chooseDevice())
        for dev in self.chooseDevice(branch,self.makeRegexMatcher()):
            (name, props) = self._emitDev(dev)
            if not self.options.noorganizers:
                # ensure that if we've pruned Organizers above this
                # Device that we emit them first
                result['DeviceClasses'] += self._backtraceOrg(outFile, dev)
            outFile.write("\n%s %s\n" % (name, ", ".join(props)))
            result['Devices'] += 1
        
        # Recurse on down the Tree
        for org in branch.children():
           found = self.listDeviceTree(outFile, org)
           result['Devices'] += found['Devices']
           result['DeviceClasses'] += found['DeviceClasses']     
        return result

    def buildOptions(self):
        """
        Add our command-line options to the basics
        """
        ZCmdBase.buildOptions(self)

        self.parser.add_option('--root',
             dest = "root", default = "",
             help = "Set the root Device Path to dump (eg: /Devices/Servers "
                    "or /Devices/Network/Cisco/Nexus; default: /Devices)")

        self.parser.add_option('-o', '--outFile',
             dest = 'outFile', default = sys.__stdout__,
             help = "Specify file to which zenbatchdump will write output")

        self.parser.add_option('--regex',
             dest = 'regex', default = '.*',
             help = "Specify include filter for device objects")

        self.parser.add_option('--prune',
             dest = 'prune', default = False,
             action = 'store_true',
             help = "Should DeviceClasses only be dumped if part of root path")

        self.parser.add_option('--allzprops',
             dest = 'allzprops', default = False,
             action = 'store_true',
             help = "Should z properties (including acquired values) be dumped?")

        self.parser.add_option('--noorganizers',
             dest = 'noorganizers', default = False,
             action = 'store_true',
             help = "Should organizers (device classes, groups, etc) be dumped?")

    def run(self):
        """
        Run the batch device dump
        """
        # make sure we have somewhere to write output
        if isinstance(self.options.outFile, str):
            try:
                outFile = open(self.options.outFile, "w")
            except IOError as e:
                self.log.error("Cannot open file %s for writing: %s",
                               self.options.outFile, e)
                sys.exit(1)
        else:
            outFile = self.options.outFile
            self.options.outFile = outFile.name

        # ensure we have a valid root
        if self.options.root:
            if self.options.root[0] == '/':
                self.options.root = self.options.root[1:]
            if not self._prepRoot():
                outFile.close()
                sys.exit(2)

        self.printHeader(outFile)
        foundLSGO = {}
        foundLSGO['Locations'] = self.listLSGOTree(outFile, self.dmd.Locations)
        foundLSGO['Systems'] = self.listLSGOTree(outFile, self.dmd.Systems)
        foundLSGO['Groups'] = self.listLSGOTree(outFile, self.dmd.Groups)
        foundDevices = self.listDeviceTree(outFile)
        self.printTrailer(outFile, foundLSGO, foundDevices)
        outFile.close()

    def printHeader(self, outFile):
        curDate = datetime.now()
        hostname = platform.node()
        outFile.write("# zenbatchdump run on host %s on date %s\n" % (hostname,str(curDate)))
        outFile.write("# with --root=%s\n" % self.options.root)
        outFile.write("# To load this Device dump file, use:\n")
        outFile.write("#   zenbatchload <file>\n")

    def printTrailer(self, outFile, foundLSGO, foundDevices):
        outFile.write("\n# Dumped:\n")
        for type in foundLSGO:
            outFile.write("#        %13s: %d\n" % (type, foundLSGO[type]))
        for type in foundDevices:
            outFile.write("#        %13s: %d\n" % (type, foundDevices[type]))


if __name__=='__main__':
    batchDumper = BatchDeviceDumper()
    batchDumper.run()
