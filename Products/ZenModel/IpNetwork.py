##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = """IpNetwork

IpNetwork represents an IP network which contains
many IP addresses.
"""

import math
import transaction
from xml.dom import minidom
import logging
log = logging.getLogger('zen')

from ipaddr import IPAddress, IPNetwork

from Globals import DTMLFile
from Globals import InitializeClass
from Acquisition import aq_base
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions
from Products.ZenModel.ZenossSecurity import *

from Products.ZenUtils.IpUtil import *
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.Search import makeCaseInsensitiveFieldIndex, makeMultiPathIndex, makeCaseSensitiveKeywordIndex\
    , makeCaseSensitiveFieldIndex
from IpAddress import IpAddress
from DeviceOrganizer import DeviceOrganizer

from Products.ZenModel.Exceptions import *

from Products.ZenUtils.Utils import isXmlRpc, setupLoggingHeader, executeCommand
from Products.ZenUtils.Utils import binPath, clearWebLoggingStream
from Products.ZenUtils import NetworkTree
from Products.ZenUtils.Utils import edgesToXML
from Products.ZenUtils.Utils import unused, zenPath
from Products.Jobber.jobs import SubprocessJob
from Products.ZenWidgets import messaging

def manage_addIpNetwork(context, id, netmask=24, REQUEST = None, version=4):
    """make a IpNetwork"""
    net = IpNetwork(id, netmask=netmask, version=version)
    context._setObject(net.id, net)
    if id.endswith("Networks"):
        net = context._getOb(net.id)
        net.dmdRootName = id
        net.buildZProperties()
        net.createCatalog()
        #manage_addZDeviceDiscoverer(context)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')


addIpNetwork = DTMLFile('dtml/addIpNetwork',globals())


# When an IP is added the default location will be
# into class A->B->C network tree
defaultNetworkTree = (32,)

class IpNetwork(DeviceOrganizer):
    """IpNetwork object"""

    isInTree = True

    buildLinks = True

    # Index name for IP addresses
    default_catalog = 'ipSearch'

    portal_type = meta_type = 'IpNetwork'

    version = 4

    _properties = (
        {'id':'netmask', 'type':'int', 'mode':'w'},
        {'id':'description', 'type':'text', 'mode':'w'},
        {'id':'version', 'type':'int', 'mode':'w'},
        )

    _relations = DeviceOrganizer._relations + (
        ("ipaddresses", ToManyCont(ToOne, "Products.ZenModel.IpAddress", "network")),
        ("clientroutes", ToMany(ToOne,"Products.ZenModel.IpRouteEntry","target")),
        ("location", ToOne(ToMany, "Products.ZenModel.Location", "networks")),
        )

    # Screen action bindings (and tab definitions)
    factory_type_information = (
        {
            'id'             : 'IpNetwork',
            'meta_type'      : 'IpNetwork',
            'description'    : """Arbitrary device grouping class""",
            'icon'           : 'IpNetwork_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addIpNetwork',
            'immediate_view' : 'viewNetworkOverview',
            'actions'        :
            (
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewNetworkOverview'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'zProperties'
                , 'name'          : 'Configuration Properties'
                , 'action'        : 'zPropertyEdit'
                , 'permissions'   : ("Manage DMD",)
                },
            )
          },
        )

    security = ClassSecurityInfo()


    def __init__(self, id, netmask=24, description='', version=4):
        if id.find("/") > -1: id, netmask = id.split("/",1)
        DeviceOrganizer.__init__(self, id, description)
        if not id.endswith("Networks"):
            checkip(id)
        self.netmask = maskToBits(netmask)
        self.version = version
        self.description = description
        self.title = ipunwrap(id)
        self.dmdRootName = "Networks"
        if version == 6:
            self.dmdRootName = "IPv6Networks"

    security.declareProtected('Change Network', 'manage_addIpNetwork')
    def manage_addIpNetwork(self, newPath, REQUEST=None):
        """
        From the GUI, create a new subnet (if necessary)
        """
        net = self.createNet(newPath)
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(net.absolute_url())

    def checkValidId(self, id, prep_id = False):
        """Checks a valid id
        """
        if id.find("/") > -1: id, netmask = id.split("/",1)
        return super(IpNetwork, self).checkValidId(id, prep_id)


    def getNetworkRoot(self, version=None):
        """This is a hook method do not remove!"""
        if not isinstance(version, int):
            version = self.version
        if version is 6:
            return self.dmd.getDmdRoot("IPv6Networks")
        return self.dmd.getDmdRoot("Networks")


    def createNet(self, netip, netmask=24):
        """
        Return and create if necessary network.  netip is in the form
        1.1.1.0/24 or with netmask passed as parameter.  Subnetworks created
        based on the zParameter zDefaulNetworkTree.
        Called by IpNetwork.createIp and IpRouteEntry.setTarget
        If the netmask is invalid, then a netmask of 24 is assumed.

        @param netip: network IP address start
        @type netip: string
        @param netmask: network mask
        @type netmask: integer
        @todo: investigate IPv6 issues
        """
        if '/' in  netip:
            netip, netmask = netip.split("/",1)

        checkip(netip)
        ipobj = IPAddress(ipunwrap_strip(netip))
        try:
            netmask = int(netmask)
        except (TypeError, ValueError):
            netmask = 24
        netmask = netmask if netmask < ipobj.max_prefixlen else 24

        #hook method do not remove!
        netroot = self.getNetworkRoot(ipobj.version)
        netobj = netroot.getNet(netip)
        if netmask == 0:
            raise ValueError("netip '%s' without netmask" % netip)
        if netobj and netobj.netmask >= netmask: # Network already exists.
            return netobj

        ipNetObj = IPNetwork(netip)
        if ipNetObj.version == 4:
            netip = getnetstr(netip, netmask)
            netTree = getattr(self, 'zDefaultNetworkTree', defaultNetworkTree)
            netTree = map(int, netTree)
            if ipobj.max_prefixlen not in netTree:
                netTree.append(ipobj.max_prefixlen)
        else:
            # IPv6 doesn't use subnet masks the same way
            netip = getnetstr(netip, 64)
            netmask = 64
            # ISPs are supposed to provide the 48-bit prefix to orgs (RFC 3177)
            netTree = (48,)

        if netobj:
            # strip irrelevant values from netTree if we're not starting at /0
            netTree = [ m for m in netTree if m > netobj.netmask ]
        else:
            # start at /Networks if no containing network was found
            netobj = netroot

        for treemask in netTree:
            if treemask >= netmask:
                netobjParent = netobj
                netobj = netobj.addSubNetwork(netip, netmask)
                self.rebalance(netobjParent, netobj)
                break
            else:
                supnetip = getnetstr(netip, treemask)
                netobjParent = netobj
                netobj = netobj.addSubNetwork(supnetip, treemask)
                self.rebalance(netobjParent, netobj)

        return netobj


    def rebalance(self, netobjParent, netobj):
        """
        Look for children of the netobj at this level and move them to the
        right spot.
        """
        moveList = []
        for subnetOrIp in netobjParent.children():
            if subnetOrIp == netobj:
                continue
            if netobj.hasIp(subnetOrIp.id):
                moveList.append(subnetOrIp.id)
        if moveList:
            netobjPath = netobj.getOrganizerName()[1:]
            netobjParent.moveOrganizer(netobjPath, moveList)

    def findNet(self, netip, netmask=0):
        """
        Find and return the subnet of this IpNetwork that matches the requested
        netip and netmask.
        """
        if netip.find("/") >= 0:
            netip, netmask = netip.split("/", 1)
            netmask = int(netmask)
        for subnet in [self] + self.getSubNetworks():
            if netmask == 0 and subnet.id == netip:
                return subnet
            if subnet.id == netip and subnet.netmask == netmask:
                return subnet
        return None


    def getNet(self, ip):
        """Return the net starting form the Networks root for ip.
        """
        return self._getNet(ipunwrap(ip))


    def _getNet(self, ip):
        """Recurse down the network tree to find the net of ip.
        """

        # If we can find the IP in the catalog, use it. This is fast.
        brains = self.ipSearch(id=ip)
        path = self.getPrimaryUrlPath()
        for brain in brains:
            bp = brain.getPath()
            if bp.startswith(path):
                try:
                    return self.unrestrictedTraverse('/'.join(bp.split('/')[:-2]))
                except KeyError:
                    pass

        # Otherwise we have to traverse the entire network hierarchy.
        for net in self.children():
            if net.hasIp(ip):
                if len(net.children()):
                    subnet = net._getNet(ip)
                    if subnet:
                        return subnet
                    else:
                        return net
                else:
                    return net


    def createIp(self, ip, netmask=24):
        """Return an ip and create if nessesary in a hierarchy of
        subnetworks based on the zParameter zDefaulNetworkTree.
        """
        ipobj = self.findIp(ip)
        if ipobj: return ipobj
        netobj = self.createNet(ip, netmask)
        ipobj = netobj.addIpAddress(ip,netmask)
        return ipobj


    def freeIps(self):
        """Number of free Ips left in this network.
        """
        freeips = 0
        try:
            net = IPNetwork(ipunwrap(self.id))
            freeips = int(math.pow(2, net.max_prefixlen - self.netmask) - self.countIpAddresses())
            if self.netmask > net.max_prefixlen:
                return freeips
            return freeips - 2
        except ValueError:
            for net in self.children():
                freeips += net.freeIps()
            return freeips


    def hasIp(self, ip):
        """
        Could this network contain this IP?
        """
        net = IPNetwork(ipunwrap(self.id))
        start = long(int(net.network))
        end = start + math.pow(2, net.max_prefixlen - self.netmask)
        return start <= numbip(ip) < end

    def fullIpList(self):
        """Return a list of all IPs in this network.
        """
        net = IPNetwork(ipunwrap(self.id))
        if (self.netmask == net.max_prefixlen): return [self.id]
        ipnumb = long(int(net))
        maxip = math.pow(2, net.max_prefixlen - self.netmask)
        start = int(ipnumb+1)
        end = int(ipnumb+maxip-1)
        return map(strip, range(start,end))


    def deleteUnusedIps(self):
        """Delete ips that are unused in this network.
        """
        for ip in self.ipaddresses():
            if ip.device(): continue
            self.ipaddresses.removeRelation(ip)


    def defaultRouterIp(self):
        """Return the ip of the default router for this network.
        It is based on zDefaultRouterNumber which specifies the sequence
        number that locates the router in this network.  If:
        zDefaultRouterNumber==1 for 10.2.1.0/24 -> 10.2.1.1
        zDefaultRouterNumber==254 for 10.2.1.0/24 -> 10.2.1.254
        zDefaultRouterNumber==1 for 10.2.2.128/25 -> 10.2.2.129
        zDefaultRouterNumber==126 for 10.2.2.128/25 -> 10.2.2.254
        """
        roffset = getattr(self, "zDefaultRouterNumber", 1)
        return strip((numbip(self.id) + roffset))


    def getNetworkName(self):
        """return the full network name of this network"""
        return "%s/%d" % (self.id, self.netmask)


    security.declareProtected('View', 'primarySortKey')
    def primarySortKey(self):
        """
        Sort by the IP numeric

        >>> net = dmd.Networks.addSubNetwork('1.2.3.0', 24)
        >>> net.primarySortKey()
        16909056L
        """
        return numbip(self.id)


    security.declareProtected('Change Network', 'addSubNetwork')
    def addSubNetwork(self, ip, netmask=24):
        """Return and add if nessesary subnetwork to this network.
        """
        netobj = self.getSubNetwork(ip)
        if not netobj:
            net = IpNetwork(ipwrap(ip), netmask=netmask, version=self.version)
            self._setObject(ipwrap(ip), net)
        return self.getSubNetwork(ip)


    security.declareProtected('View', 'getSubNetwork')
    def getSubNetwork(self, ip):
        """get an ip on this network"""
        return self._getOb(ipwrap(ip), None)


    def getSubNetworks(self):
        """Return all network objects below this one.
        """
        nets = self.children()
        for subgroup in self.children():
            nets.extend(subgroup.getSubNetworks())
        return nets

    security.declareProtected('Change Network', 'addIpAddress')
    def addIpAddress(self, ip, netmask=24):
        """add ip to this network and return it"""
        ipobj = IpAddress(ip,netmask)
        self.ipaddresses._setObject(ipwrap(ip), ipobj)
        return self.getIpAddress(ip)


    security.declareProtected('View', 'getIpAddress')
    def getIpAddress(self, ip):
        """get an ip on this network"""
        return self.ipaddresses._getOb(ipwrap(ip), None)

    security.declareProtected('Change Network', 'manage_deleteIpAddresses')
    def manage_deleteIpAddresses(self, ipaddresses=(), REQUEST=None):
        """Delete ipaddresses by id from this network.
        """
        for ipaddress in ipaddresses:
            ip = self.getIpAddress(ipaddress)
            self.ipaddresses.removeRelation(ip)
        if REQUEST:
            return self.callZenScreen(REQUEST)


    security.declareProtected('View', 'countIpAddresses')
    def countIpAddresses(self, inuse=False):
        """get an ip on this network"""
        if inuse:
            # When there are a large number of IPs this code is too slow
            # we either need to cache all /Status/Ping events before hand
            # and then integrate them with the list of IPs
            # or blow off the whole feature.  For now we just set the
            # default to not use this code.  -EAD
            count = len(filter(lambda x: x.getStatus() == 0,self.ipaddresses()))
        else:
            count = self.ipaddresses.countObjects()
        for net in self.children():
            count += net.countIpAddresses(inuse)
        return count

    security.declareProtected('View', 'countDevices')
    countDevices = countIpAddresses


    def getAllCounts(self, devrel=None):
        """Count all devices within a device group and get the
        ping and snmp counts as well"""
        unused(devrel)
        counts = [
            self.ipaddresses.countObjects(),
            self._status("Ping", "ipaddresses"),
            self._status("Snmp", "ipaddresses"),
        ]
        for group in self.children():
            sc = group.getAllCounts()
            for i in range(3): counts[i] += sc[i]
        return counts


    def pingStatus(self, devrel=None):
        """aggregate ping status for all devices in this group and below"""
        unused(devrel)
        return DeviceOrganizer.pingStatus(self, "ipaddresses")


    def snmpStatus(self, devrel=None):
        """aggregate snmp status for all devices in this group and below"""
        unused(devrel)
        return DeviceOrganizer.snmpStatus(self, "ipaddresses")


    def getSubDevices(self, filter=None):
        """get all the devices under and instance of a DeviceGroup"""
        return DeviceOrganizer.getSubDevices(self, filter, "ipaddresses")


    def findIp(self, ip):
        """Find an ipAddress.
        """
        searchCatalog = self.getNetworkRoot().ipSearch
        ret = searchCatalog(dict(id=ipwrap(ip)))
        if not ret: return None
        if len(ret) > 1:
            raise IpAddressConflict( "IP address conflict for IP: %s" % ip )
        return ret[0].getObject()


    def buildZProperties(self):
        if self.version == 6:
            nets = self.getDmdRoot("IPv6Networks")
        else:
            nets = self.getDmdRoot("Networks")
        if getattr(aq_base(nets), "zDefaultNetworkTree", False):
            return
        nets._setProperty("zDefaultNetworkTree", (64,128) if nets.id == "IPv6Networks" else (24,32), type="lines")
        nets._setProperty("zDrawMapLinks", True, type="boolean")
        nets._setProperty("zAutoDiscover", True, type="boolean")
        nets._setProperty("zPingFailThresh", 168, type="int")
        nets._setProperty("zIcon", "/zport/dmd/img/icons/network.png")
        nets._setProperty("zPreferSnmpNaming", False, type="boolean")
        nets._setProperty("zSnmpStrictDiscovery", False, type="boolean")


    def reIndex(self):
        """Go through all ips in this tree and reindex them."""
        zcat = self._getCatalog()
        zcat.manage_catalogClear()
        for net in self.getSubNetworks():
            for ip in net.ipaddresses():
                ip.index_object()


    def createCatalog(self):
        """make the catalog for device searching"""
        from Products.ZCatalog.ZCatalog import manage_addZCatalog

        # XXX convert to ManagableIndex
        manage_addZCatalog(self, self.default_catalog,
                            self.default_catalog)
        zcat = self._getOb(self.default_catalog)
        cat = zcat._catalog
        cat.addIndex('id', makeCaseInsensitiveFieldIndex('id'))

        zcat._catalog.addIndex('ipAddressAsInt',  makeCaseSensitiveFieldIndex('ipAddressAsInt'))
        zcat._catalog.addIndex('path', makeMultiPathIndex('path'))


    def discoverNetwork(self, REQUEST=None):
        """
        """
        path = '/'.join(self.getPrimaryPath()[4:])
        return self.discoverDevices([path], REQUEST=REQUEST)

    def discoverDevices(self, organizerPaths=None, REQUEST = None):
        """
        Load a device into the database connecting its major relations
        and collecting its configuration.
        """
        xmlrpc = isXmlRpc(REQUEST)

        if not organizerPaths:
            if xmlrpc: return 1
            return self.callZenScreen(REQUEST)

        zDiscCommand = "empty"

        from Products.ZenUtils.ZenTales import talesEval

        orgroot = self.getNetworkRoot()
        for organizerName in organizerPaths:
            organizer = orgroot.getOrganizer(organizerName)
            if organizer is None:
                if xmlrpc: return 1 # XML-RPC error
                log.error("Couldn't obtain a network entry for '%s' "
                            "-- does it exist?" % organizerName)
                continue

            zDiscCommand = getattr(organizer, "zZenDiscCommand", None)
            if zDiscCommand:
                cmd = talesEval('string:' + zDiscCommand, organizer).split(" ")
            else:
                cmd = ["zendisc", "run", "--net", organizer.getNetworkName()]
                if getattr(organizer, "zSnmpStrictDiscovery", False):
                    cmd += ["--snmp-strict-discovery"]
                if getattr(organizer, "zPreferSnmpNaming", False):
                    cmd += ["--prefer-snmp-naming"]
            zd = binPath('zendisc')
            zendiscCmd = [zd] + cmd[1:]
            status = self.dmd.JobManager.addJob(SubprocessJob,
                description="Discover devices in network %s" % organizer.getNetworkName(),
                args=(zendiscCmd,))

        log.info('Done')

        if REQUEST and not xmlrpc:
            REQUEST.RESPONSE.redirect('/zport/dmd/JobManager/joblist')

        if xmlrpc: return 0


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
        alog = logging.getLogger()
        if getattr(self, "_v_handler", False):
            alog.removeHandler(self._v_handler)


    def loaderFooter(self, response):
        """add navigation links to the end of the loader output"""
        response.write("""<tr class="tableheader"><td colspan="4">
            Navigate to network <a href=%s>%s</a></td></tr>"""
            % (self.absolute_url(), self.id))
        response.write("</table></body></html>")

    security.declareProtected('View', 'getXMLEdges')
    def getXMLEdges(self, depth=1, filter='/', start=()):
        """ Gets XML """
        if not start: start=self.id
        edges = NetworkTree.get_edges(self, depth,
                                      withIcons=True, filter=filter)
        return edgesToXML(edges, start)

    def getIconPath(self):
        """ gets icon """
        try:
            return self.primaryAq().zIcon
        except AttributeError:
            return '/zport/dmd/img/icons/noicon.png'


    def urlLink(self, text=None, url=None, attrs={}):
        """
        Return an anchor tag if the user has access to the remote object.
        @param text: the text to place within the anchor tag or string.
                     Defaults to the id of this object.
        @param url: url for the href. Default is getPrimaryUrlPath
        @type attrs: dict
        @param attrs: any other attributes to be place in the in the tag.
        @return: An HTML link to this object
        @rtype: string
        """
        if not text:
            text = "%s/%d" % (self.id, self.netmask)
        if not self.checkRemotePerm("View", self):
            return text
        if not url:
            url = self.getPrimaryUrlPath()
        if len(attrs):
            return '<a href="%s" %s>%s</a>' % (url,
                ' '.join('%s="%s"' % (x,y) for x,y in attrs.items()),
                text)
        else:
            return '<a href="%s">%s</a>' % (url, text)

InitializeClass(IpNetwork)


class AutoDiscoveryJob(SubprocessJob):
    """
    Job encapsulating autodiscovery over a set of IP addresses.

    Accepts a list of strings describing networks OR a list of strings
    specifying IP ranges, not both. Also accepts a set of zProperties to be
    set on devices that are discovered.
    """
    def _run(self, nets=(), ranges=(), zProperties=(), collector='localhost'):
        # Store the nets and ranges
        self.nets = nets
        self.ranges = ranges

        # Store zProperties on the job
        if zProperties:
            self.setProperties(**zProperties)
        # Build the zendisc command
        cmd = self.dmd.Monitors.getPerformanceMonitor(collector)._getZenDiscCommand(
            '', '/Discovered', collector, 1000
            )
        # strip out the device option since we are discovering for a network
        cmd = [c.replace(" -d ", "") for c in cmd if c != '-d']
        cmd.extend([
                '--parallel', '8',
                '--job', self.request.id
                   ])
        if not self.nets and not self.ranges:
            # Gotta have something
            self.log.error("Must pass in either a network or a range.")
        elif self.nets and self.ranges:
            # Can't have both
            self.log.error("Must pass in either networks or ranges, not both")
        else:
            if self.nets:
                for net in self.nets:
                    cmd.extend(['--net', net])
            elif self.ranges:
                for iprange in self.ranges:
                    cmd.extend(['--range', iprange])
            SubprocessJob._run(self, cmd)


class IpNetworkPrinter(object):

    def __init__(self, out):
        """out is the output stream to print to"""
        self._out = out


class TextIpNetworkPrinter(IpNetworkPrinter):
    """
    Prints out IpNetwork hierarchy as text with indented lines.
    """

    def printIpNetwork(self, net):
        """
        Print out the IpNetwork and IpAddress hierarchy under net.
        """
        self._printIpNetworkLine(net)
        self._printTree(net)

    def _printTree(self, net, indent="  "):
        for child in net.children():
            self._printIpNetworkLine(child, indent)
            self._printTree(child, indent + "  ")
        for ipaddress in net.ipaddresses():
            args = (indent, ipaddress, ipaddress.__class__.__name__)
            self._out.write("%s%s (%s)\n" % args)

    def _printIpNetworkLine(self, net, indent=""):
        args = (indent, net.id, net.netmask, net.__class__.__name__)
        self._out.write("%s%s/%s (%s)\n" % args)


class PythonIpNetworkPrinter(IpNetworkPrinter):
    """
    Prints out the IpNetwork hierarchy as a python dictionary.
    """

    def printIpNetwork(self, net):
        """
        Print out the IpNetwork and IpAddress hierarchy under net.
        """
        tree = {}
        self._createTree(net, tree)
        from pprint import pformat
        self._out.write("%s\n" % pformat(tree))

    def _walkTree(self, net, tree):
        for child in net.children():
            self._createTree(child, tree)
        for ip in net.ipaddresses():
            key = (ip.__class__.__name__, ip.id, ip.netmask)
            tree[key] = True

    def _createTree(self, net, tree):
        key = (net.__class__.__name__, net.id, net.netmask)
        subtree = {}
        tree[key] = subtree
        self._walkTree(net, subtree)


class XmlIpNetworkPrinter(IpNetworkPrinter):
    """
    Prints out the IpNetwork hierarchy as XML.
    """

    def printIpNetwork(self, net):
        """
        Print out the IpNetwork and IpAddress hierarchy under net.
        """
        self._doc = minidom.parseString('<root/>')
        root = self._doc.documentElement
        self._createTree(net, root)
        self._out.write(self._doc.toprettyxml())

    def _walkTree(self, net, tree):
        for child in net.children():
            self._createTree(child, tree)
        for ip in net.ipaddresses():
            self._appendChild(tree, ip)

    def _createTree(self, net, tree):
        node = self._appendChild(tree, net)
        self._walkTree(net, node)

    def _appendChild(self, tree, child):
        node = self._doc.createElement(child.__class__.__name__)
        node.setAttribute("id", child.id)
        node.setAttribute("netmask", str(child.netmask))
        tree.appendChild(node)
        return node


class IpNetworkPrinterFactory(object):

    def __init__(self):
        self._printerFactories = {'text': TextIpNetworkPrinter,
                                  'python': PythonIpNetworkPrinter,
                                  'xml': XmlIpNetworkPrinter}

    def createIpNetworkPrinter(self, format, out):
        if format in self._printerFactories:
            factory = self._printerFactories[format]
            return factory(out)
        else:
            args = (format, self._printerFactories.keys())
            raise Exception("Invalid format '%s' must be one of %s" % args)
