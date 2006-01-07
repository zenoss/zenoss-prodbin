#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

import sys
import socket
import logging

from Products.ZenEvents.ZenEventClasses import PingStatus
from Ping import PingJob

global allnodes, netsmap, devicemap
allnodes = []
netsmap = {}

plog = logging.getLogger("zen.PingMonitor")

class Rnode(object):
    """Rnode is a router node in the tree map.
    """

    def __init__(self, ip, devname, status, parent=None):
        self.pj = PingJob(ip, devname, status, 20)
        self.pj.parent = parent
        self.parent = parent
        self.children = []
        self.nets = []
        if not parent: 
            global devicemap
            self.addNet("default","default")
            devicemap = {devname:1}


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


    def hasDev(self, devname):
        global devicemap
        return devicemap.has_key(devname)


    def hasNet(self, netname):
        global netsmap
        return netsmap.has_key(netname)


    def addRouter(self, ip, devname, status):
        global devicemap
        if devicemap.has_key(devname): return devicemap[devname]
        devicemap[devname] = 1
        child = Rnode(ip, devname, status, self)
        self.children.append(child)
        return child


    def addNet(self, netip, enterip):
        global netsmap
        if self.hasNet(netip): return netsmap[netip]
        net = Net(netip, enterip, self)
        self.nets.append(net)
        netsmap[netip] = net
        return net


    def getNet(self, netname):
        """Return the net node for net name
        """
        global netsmap
        net = netsmap.get(netname,None)
        if not net: net = netsmap['default']
        return net


    def addDevice(self, device, cycle):
        """Add a device to the ping tree.
        """
        global devicemap
        if self.hasDev(device.id): 
            plog.debug("device '%s' already exists.", device.id)
            return
        devicemap[device.id] = 1
        mint = device.getManageInterface()
        netname = mint.getNetworkName()
        net = self.getNet(netname)
        if net.ip == 'default':
            plog.warn("device '%s' network '%s' not in topology", 
                            device.id, netname)
        pj = PingJob(mint.getIp(), device.id, 
                    device.getStatus(PingStatus), cycle)
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

    
    def pprint_old(self, nodes=None):
        global allnodes
        if nodes is None: 
            nodes = [self,]
            for n in allnodes:
                n._seen=False
            allnodes = []
        nnodes = []
        for node in nodes:
            if getattr(node, "_seen", False): continue
            node._seen = True
            allnodes.append(node)
            print node
            nnodes.extend(node.children)
        print
        if nnodes: self.pprint_old(nnodes)

    
    def pprint(self, root=None):
        if root is None: root = self
        yield root
        last = root
        for node in self.pprint(root):
            for child in iter(node.children):
                yield child
                last = child
            if last == node: return    

    
    def __str__(self):
        return "%s->(%s)" % (self.pj.ipaddr, ",".join(map(str,self.nets)))



class Net(object):
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
            pj.reset()
            yield pj
  
    def addPingJob(self, pj):
        self.pingjobs.append(pj)

    def reset(self):
        map(lambda x: x.reset(), self.pingjobs)

    def __str__(self):
        return self.ip


def buildTree(root, rootnode=None, devs=None, memo=None):
    """Returns tree where tree that maps the network from root's 
    perspective  and nmap is a dict that points network ids to the 
    network objects in the tree.  nmap is used to add devices to be pinged
    to the tree.
    """
    if memo is None: memo = []
    if devs is None: 
        mint = root.getManageInterface()
        rootnode = Rnode(mint.getIp(), root.id, root.getStatus(PingStatus))
        devs = [(root,rootnode)]
    nextdevs = []
    for dev, rnode in devs:
        if dev.id in memo: return
        logging.debug("mapping device '%s'", dev.id)
        memo.append(dev.id)
        for route in dev.os.routes():
            if route.getNextHopIp() == "0.0.0.0":
                if not route.getTarget().startswith("127."):
                    netid = route.getTarget()
                    if rootnode.hasNet(netid): continue
                    net = rnode.addNet(netid,route.getInterfaceIp())
                    logging.debug("add net: %s to rnode: %s", net, rnode)
            else:
                ndev = route.getNextHopDevice()
                if ndev: 
                    if rootnode.hasDev(ndev.id): continue
                    nrnode = rnode.addRouter(route.getNextHopIp(),ndev.id,
                                                ndev.getStatus(PingStatus))
                    logging.debug("create rnode: %s", nrnode)
                    nextdevs.append((ndev, nrnode))
    if nextdevs: buildTree(root, rootnode, nextdevs, memo)
    return rootnode



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
        logging.debug("mapping device '%s' distance '%s'", dev.id, distance)
        memo.append(dev.id)
        for route in dev.os.routes():
            if route.getNextHopIp() == "0.0.0.0":
                if not route.getTarget().startswith("127."):
                    netip = route.getTargetIp()
                    curdist = nmap.get(netip,sys.maxint)
                    if curdist > distance:
                        logging.debug("netip '%s' distance '%d'", 
                                        netip, distance)
                        nmap[netip] = distance
            else:
                ndev = route.getNextHopDevice()
                if ndev: nextdevs.append(ndev)
    distance += 1
    netDistMap(root, nmap, distance, nextdevs, memo)
    return nmap


