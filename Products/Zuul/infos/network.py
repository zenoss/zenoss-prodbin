##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import re
from itertools import imap
from zope.interface import implements
from zope.component import adapts
from Products.AdvancedQuery import In, Eq
from Products.ZenModel.IpNetwork import IpNetwork
from Products.ZenModel.IpAddress import IpAddress
from Products.ZenUtils.IpUtil import ipToDecimal
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.Zuul.catalog.model_catalog import SearchResults, OBJECT_UID_FIELD as UID
from Products.Zuul.interfaces import IIpNetworkInfo, IIpAddressInfo, IIpNetworkNode
from Products.Zuul.infos import InfoBase, BulkLoadMixin
from Products.Zuul.decorators import info
from Products.Zuul.utils import getZPropertyInfo, setZPropertyInfo
from Products.Zuul.tree import TreeNode


class NetworkTree(object):
    def __init__(self, path):
        self.path = path
        self.netip = path.split("/")[-1]
        self.subnets = {}
        self.partial_ip_count = 0   # count not including children
        self.total_ip_count = 0     # count including children


class NetworkTreeCache(object):
    def __init__(self, root):
        self.root = root              # IpNetwork for which we are building the tree
        self.brains = {}              # net_uid : net brain
        self.network_trees = {}       # net_uid : NetworkTree
        self.root_network_tree = None

        self.build_network_tree()
        self.load_brains()
        self.load_ip_counts()

    def build_network_tree(self):
        """
        Builds the network tree for a given network and its subnetworks
        The network tree is built using the networks paths that are available
        in the network_cache
        """
        net_obj = self.root
        root = net_obj.getNetworkRoot()

        # get the paths of all relevant networks
        paths = []
        if root == net_obj: # we are at the nerwork root
            for nets in root.network_cache.cache.itervalues():
                paths.extend(nets)
        else:
            paths = root.network_cache.get_subnets_paths(net_obj)

        self.root_network_tree = NetworkTree("/".join(net_obj.getPrimaryPath()))
        parent_path = self.root_network_tree.path
        self.network_trees[parent_path] = self.root_network_tree
        # iterate through all networks paths creating network nodes in the network tree
        for path in paths:
            if not path.startswith(parent_path) or \
               path == parent_path:
                continue
            current_path = parent_path
            current_tree = self.root_network_tree
            # create subnets from the path
            # Example path /zport/dmd/Networks/10.0.0.0/10.10.0.0/10.10.10.0
            # creates subnets 10.0.0.0, 10.0.0.0/10.10.0.0 and 10.0.0.0/10.10.0.0/10.10.10.0
            nets = path.replace(parent_path, "").strip("/").split("/")
            for netip in nets:
                if not netip:
                    continue
                current_path = "{}/{}".format(current_path, netip)
                if netip not in current_tree.subnets:
                    new_network_tree = NetworkTree(current_path)
                    current_tree.subnets[netip] = new_network_tree
                    self.network_trees[current_path] = new_network_tree
                current_tree = current_tree.subnets[netip]

    def _load_brains(self, batch):
        model_catalog = IModelCatalogTool(self.root.dmd)
        fields = [ UID, "name", "id", "uuid" ]
        query = In(UID, batch)
        search_results = model_catalog.search(query=query, fields=fields)
        for brain in search_results.results:
            path = brain.getPath()
            self.brains[path] = brain

    def load_brains(self):
        """
        Get the brains of all the relevant networks
        """
        batch = []
        batch_size = 1000
        for uid in self.network_trees.iterkeys():
            batch.append('"{0}"'.format(uid))
            if len(batch) == batch_size:
                self._load_brains(batch)
                batch = []
        if batch:
            self._load_brains(batch)

    def load_ip_counts(self):
        # Load all ip addresses to get count of ips per net
        # @TODO We should do this using solr facets
        model_catalog = IModelCatalogTool(self.root.dmd)
        query = Eq("objectImplements", 'Products.ZenModel.IpAddress.IpAddress')
        search_results = model_catalog.search(query=query, fields="networkId")
        for ip_brain in search_results.results:
            if ip_brain.networkId in self.network_trees:
                self.network_trees[ip_brain.networkId].partial_ip_count += 1

        # Now get the total ip count per net including subnets from the bottom up
        net_uids = self.network_trees.keys()
        net_uids.sort(reverse=True, key=lambda x: len(x))
        for net_uid in net_uids:
            net_tree = self.network_trees[net_uid]
            children_count = 0
            for subnet_tree in net_tree.subnets.itervalues():
                children_count += subnet_tree.total_ip_count
            net_tree.total_ip_count = net_tree.partial_ip_count + children_count

    def get_ip_count(self, net_uid):
        count = 0
        net_tree = self.network_trees.get(net_uid)
        if net_tree:
            count = net_tree.total_ip_count
        return count

    def get_children(self, uid):
        if not uid.startswith("/zport/dmd"):
            uid = "{}/{}".format("/zport/dmd", uid)
        network_tree = self.network_trees[uid]
        subnets = network_tree.subnets.values()
        subnets.sort( key=lambda x: ipToDecimal(x.netip) )
        brains = [ self.brains[subnet.path] for subnet in subnets if self.brains.get(subnet.path)]
        return brains


class IpNetworkNode(TreeNode):
    implements(IIpNetworkNode)
    adapts(IpNetwork)

    @property
    def text(self):
        numInstances = self._get_cache.get_ip_count(self.uid)
        text = super(IpNetworkNode, self).text + '/' + str(self._object.getObject().netmask)
        return {
            'text': text,
            'count': numInstances,
            'description': 'ips'
        }

    @property
    def _get_cache(self):
        cache = getattr(self._root, '_cache', None)
        if cache is None:
            cache = NetworkTreeCache(self._root._get_object())
            setattr(self._root, '_cache', cache)
        return cache

    @property
    def children(self):
        nets = self._get_cache.get_children(self.uid)
        return imap(lambda x:IpNetworkNode(x, self._root, self), nets)

    @property
    def leaf(self):
        nets = self._get_cache.get_children(self.uid)
        return not nets

    @property
    def iconCls(self):
        return  ''


class IpNetworkInfo(InfoBase):
    implements(IIpNetworkInfo)

    @property
    def name(self):
        return self._object.getNetworkName()

    @property
    def ipcount(self):
        return str(self._object.countIpAddresses()) + '/' + \
               str(self._object.freeIps())

    # zProperties
    def getZAutoDiscover(self):
        def translate(rawValue):
            return {False: 'No', True: 'Yes'}[rawValue]
        return getZPropertyInfo(self._object, 'zAutoDiscover', True, translate)

    def setZAutoDiscover(self, data):
        setZPropertyInfo(self._object, 'zAutoDiscover', **data)

    zAutoDiscover = property(getZAutoDiscover, setZAutoDiscover)

    def getZDrawMapLinks(self):
        def translate(rawValue):
            return {False: 'No', True: 'Yes'}[rawValue]
        return getZPropertyInfo(self._object, 'zDrawMapLinks', True, translate)

    def setZDrawMapLinks(self, data):
        setZPropertyInfo(self._object, 'zDrawMapLinks', **data)

    zDrawMapLinks = property(getZDrawMapLinks, setZDrawMapLinks)

    def getZDefaultNetworkTree(self):
        def translate(rawValue):
            return ', '.join(str(x) for x in rawValue)
        return getZPropertyInfo(self._object, 'zDefaultNetworkTree',
                                translate=translate, translateLocal=True)

    _decimalDigits = re.compile('\d+')

    def setZDefaultNetworkTree(self, data):

        # convert data['localValue'] (string with comma and whitespace
        # delimeters) to tuple of integers
        digits = self._decimalDigits.findall( data['localValue'] )
        data['localValue'] = tuple( int(x) for x in digits )

        setZPropertyInfo(self._object, 'zDefaultNetworkTree', **data)

    zDefaultNetworkTree = property(getZDefaultNetworkTree, setZDefaultNetworkTree)

    def getZPingFailThresh(self):
        return getZPropertyInfo(self._object, 'zPingFailThresh')

    def setZPingFailThresh(self, data):
        setZPropertyInfo(self._object, 'zPingFailThresh', **data)

    zPingFailThresh = property(getZPingFailThresh, setZPingFailThresh)

    def getZIcon(self):
        return getZPropertyInfo(self._object, 'zIcon')

    def setZIcon(self, data):
        setZPropertyInfo(self._object, 'zIcon', **data)

    zIcon = property(getZIcon, setZIcon)

    def getZSnmpStrictDiscovery(self):
        def translate(rawValue):
            return {False: 'No', True: 'Yes'}[rawValue]
        return getZPropertyInfo(self._object, 'zSnmpStrictDiscovery', True, translate)

    def setZSnmpStrictDiscovery(self, data):
        setZPropertyInfo(self._object, 'zSnmpStrictDiscovery', **data)

    zSnmpStrictDiscovery = property(getZSnmpStrictDiscovery, setZSnmpStrictDiscovery)

    def getZPreferSnmpNaming(self):
        def translate(rawValue):
            return {False: 'No', True: 'Yes'}[rawValue]
        return getZPropertyInfo(self._object, 'zPreferSnmpNaming', True, translate)

    def setZPreferSnmpNaming(self, data):
        setZPropertyInfo(self._object, 'zPreferSnmpNaming', **data)

    zPreferSnmpNaming = property(getZPreferSnmpNaming, setZPreferSnmpNaming)

class IpAddressInfo(InfoBase, BulkLoadMixin):
    implements(IIpAddressInfo)

    @property
    @info
    def device(self):
        return self._object.device()

    @property
    def netmask(self):
        return str(self._object._netmask)

    @property
    @info
    def interface(self):
        return self._object.interface()

    @property
    def macAddress(self):
        return self._object.getInterfaceMacAddress()

    @property
    def interfaceDescription(self):
        return self._object.getInterfaceDescription()

    @property
    def pingstatus(self):
        cachedValue = self.getBulkLoadProperty('pingstatus')
        if cachedValue is not None:
            return cachedValue
        if not self._object.interface():
            return 5
        return self._object.getPingStatus()

    @property
    def snmpstatus(self):
        cachedValue = self.getBulkLoadProperty('snmpstatus')
        if cachedValue is not None:
            return cachedValue
        if not self._object.interface():
            return 5
        return self._object.getSnmpStatus()
