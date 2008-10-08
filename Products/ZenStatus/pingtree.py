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

import sys
import logging
log = logging.getLogger("zen.ZenStatus")

from Products.ZenEvents.ZenEventClasses import Status_Ping
from Products.ZenUtils.Utils import localIpCheck
from Products.ZenStatus.AsyncPing import PingJob

from twisted.spread import pb

def getStatus(device):
    # if there's a down event in the database, it must have failed twice
    status = device.getStatus(Status_Ping)
    if status == 1:
        status += 2
    return status


class RouterNode(pb.Copyable, pb.RemoteCopy):
    """RouterNode is a router node in the tree map.
    """

    def __init__(self, ip, devname, status, parent=None):
        self.pj = PingJob(ip, devname, status, 20)
        self.pj.parent = parent
        self.parent = parent
        self.children = []
        self.nets = []


    def checkpath(self):
        """Walk back up the path to the ping server looking for failed routers.
        """
        node = self
        while node.parent and node.pj.status == 0:
            node = node.parent
        if node.parent: return node.pj.hostname


    def routerpj(self):
        """Return the pingJob of our parent router.
        """
        return self.pj


    def hasDev(self, tree, devname):
        return tree.deviceMap.has_key(devname)


    def hasNet(self, tree, netname):
        return tree.netsMap.has_key(netname)


    def addRouter(self, tree, ip, devname, status):
        if tree.deviceMap.has_key(devname):
            return tree.deviceMap[devname]
        tree.deviceMap[devname] = 1
        child = RouterNode(ip, devname, status, self)
        self.children.append(child)
        return child


    def addNet(self, tree, netip, enterip):
        if self.hasNet(tree, netip):
            return tree.netsMap[netip]
        net = Net(netip, enterip, self)
        self.nets.append(net)
        tree.netsMap[netip] = net
        return net


    def getNet(self, tree, netname):
        """Return the net node for net name
        """
        net = tree.netsMap.get(netname,None)
        if not net:
            net = tree.netsMap['default']
        return net


    def addDevice(self, tree, device):
        """Add a device to the ping tree.
        """
        if self.hasDev(tree, device.id): 
            log.debug("device '%s' already exists.", device.id)
            return
        tree.deviceMap[device.id] = 1
        ip = device.getManageIp()
        if not ip: 
            return
        netobj = device.getDmdRoot("Networks").getNet(ip)
        netname = "default"
        if netobj:
            netname = netobj.getNetworkName()
        net = self.getNet(tree, netname)
        if net.ip == 'default':
            log.warn("device '%s' network '%s' not in topology", 
                            device.id, netname)
        pj = PingJob(ip, device.id, getStatus(device))
        net.addPingJob(pj)
        pj.parent = net


    def pjgen(self):
        self.pj.reset()
        yield self.pj
        if self.pj.status != 0: return 
        for rnode in self.children:
            for pj in rnode.pjgen():
                yield pj
        for net in iter(self.nets):
            for pj in net.pjgen():
                yield pj

    
    def pprint(self):
        allNodes = set()
        def recurse(nodes):
            nnodes = []
            for node in nodes:
                if node in allNodes:
                    continue
                allNodes.add(node)
                print node
                nnodes.extend(node.children)
            print
            return nnodes
        return recurse([self,])


    def pprint_gen(self, root=None):
        if root is None: root = self
        yield root
        last = root
        for node in self.pprint(root):
            for child in iter(node.children):
                yield child
                last = child
            if last == node: return    

    
    def __str__(self):
        return "%s->(%s)" % (self.pj.ipaddr, ", ".join(map(str,self.nets)))

pb.setUnjellyableForClass(RouterNode, RouterNode)


class Net(pb.Copyable, pb.RemoteCopy):
    """Net object represents a network in the tree map.
    """
    def __init__(self,ip,enterip,parent):
        self.ip = ip
        self.enterip = enterip
        self.parent = parent
        self.pingjobs = []


    def checkpath(self):
        """Walk back up the path to the ping server.
        """
        return self.parent.checkpath()


    def routerpj(self):
        """Return the pingJob of our parent router.
        """
        return self.parent.pj


    def pjgen(self):
        for pj in self.pingjobs:
            yield pj
  
    def addPingJob(self, pj):
        self.pingjobs.append(pj)

    def reset(self):
        map(lambda x: x.reset(), self.pingjobs)

    def __str__(self):
        return self.ip

pb.setUnjellyableForClass(Net, Net)

class PingTree(pb.Copyable, pb.RemoteCopy):

    deviceMap = None
    netsMap = None
    root = None

    def __init__(self, devname):
        self.netsMap = {}
        self.deviceMap = {devname:1}
        self.root = None

    def rootNode(self):
        return self.root

    def hasDev(self, device):
        return self.deviceMap.has_key(device)

    def addDevice(self, device):
        self.root.addDevice(self, device)


pb.setUnjellyableForClass(PingTree, PingTree)


def buildTree(root, rootnode=None, devs=None, memo=None, tree=None):
    """Returns tree where tree that maps the network from root's 
    perspective  and nmap is a dict that points network ids to the 
    network objects in the tree.  nmap is used to add devices to be pinged
    to the tree.
    """
    if memo is None: memo = []
    if devs is None:
        assert tree is None
        tree = PingTree(root.id)
        ipaddr = root.getManageIp()
        if not ipaddr:
            raise ValueError("zenping host %s has no manage ip"%root.id)
        rootnode = RouterNode(ipaddr, root.id, getStatus(root))
        tree.root = rootnode
        rootnode.addNet(tree, "default", "default")
        devs = [(root,rootnode)]
    nextdevs = []
    for dev, rnode in devs:
        if dev.id in memo: return
        log.debug("mapping device '%s'", dev.id)
        memo.append(dev.id)
        for route in dev.os.routes():
            if route.routetype == "direct":
                netid = route.getTarget()
                if not route.ipcheck(netid):
                    netid = route.getTarget()
                    if rootnode.hasNet(tree, netid): continue
                    net = rnode.addNet(tree, netid,route.getInterfaceIp())
                    log.debug("add net: %s to rnode: %s", net, rnode)
            else:
                ndev = route.getNextHopDevice()
                if ndev: 
                    if rootnode.hasDev(tree, ndev.id): continue
                    if route.getNextHopDevice():
                        nextHopIp = route.getNextHopDevice().manageIp
                    else:
                        nextHopIp = route.getNextHopIp()
                    nrnode = rnode.addRouter(tree,
                                             nextHopIp,ndev.id,
                                             getStatus(ndev))
                    log.debug("create rnode: %s", nrnode)
                    nextdevs.append((ndev, nrnode))
        for iface in dev.os.interfaces():
            for ip in iface.ipaddresses():
                netid = ip.getNetworkName()
                if not netid: continue
                if localIpCheck(dev, netid) or rootnode.hasNet(tree, netid): continue
                net = rnode.addNet(tree, netid,ip.getIp())
                log.debug("add net: %s to rnode: %s", net, rnode)
    if nextdevs:
        buildTree(root, rootnode, nextdevs, memo, tree)
    return tree




def netDistMap(root, nmap=None, distance=0, devs=None, memo=None):
    """Return a mapping object with network ip as key and distance as value.
    This is a recursive method that does a breadth first search of the route
    space.  It is called with no parameters (they are used by the recursion)
    """
    if nmap is None: nmap = {}
    if memo is None: memo = []
    if devs is None: devs = [root,]
    nextdevs = []
    for dev in devs:
        if dev.id in memo: return
        log.debug("mapping device '%s' distance '%s'", dev.id, distance)
        memo.append(dev.id)
        for route in dev.os.routes():
            if route.routetype == "direct":
                netid=route.getTarget()
                if not route.ipcheck(netid):
                    netip = route.getTargetIp()
                    curdist = nmap.get(netip,sys.maxint)
                    if curdist > distance:
                        log.debug("netip '%s' distance '%d'", 
                                        netip, distance)
                        nmap[netip] = distance
            else:
                ndev = route.getNextHopDevice()
                if ndev: nextdevs.append(ndev)
    distance += 1
    netDistMap(root, nmap, distance, nextdevs, memo)
    return nmap


