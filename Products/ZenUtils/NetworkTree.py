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

def _fromDeviceToNetworks(dev):
    for iface in dev.os.interfaces():
        for ip in iface.ipaddresses():
            net = ip.network()
            if net is None:
                continue
            else:
                yield net

def _fromNetworkToDevices(net, devclass):
    for ip in net.ipaddresses():
        dev = ip.device()
        if dev is None:
            continue
        dcp = dev.getDeviceClassPath()
        if not ( dcp.startswith(devclass) or 
            dcp.startswith('/Network/Router')):
            continue
        else:
            yield dev

def _get_related(node, devclass='/'):
    if node.meta_type=='IpNetwork':
        children = _fromNetworkToDevices(node, devclass)
    elif node.meta_type=='Device':
        children = _fromDeviceToNetworks(node)
    else:
        raise NotImplementedError
    return children

def _sortedpair(x,y):
    l = [x,y]
    cmpf = lambda x,y:int(x.meta_type=='Device')-int(y.meta_type=='Device')
    l.sort(cmpf)
    return tuple(l)

def _get_connections(rootnode, depth=1, pairs=[]):
    """ Depth-first search of the network tree emanating from
        rootnode, returning (network, device) edges.
    """
    if depth:
        for node in _get_related(rootnode):
            sorted = _sortedpair(rootnode, node)
            pair = [x.id for x in sorted]
            if pair not in pairs:
                pairs.append(pair)
                yield sorted
                for childnode in _get_related(node):
                    for n in _get_connections(childnode, depth-1, pairs):
                        yield n

def get_edges(rootnode, depth=1, withIcons=False):
    """ Returns some edges """
    g = _get_connections(rootnode, depth, [])
    for nodea, nodeb in g:
        if withIcons:
            yield ((nodea.id, nodea.getIconPath()),
                   (nodeb.id, nodeb.getIconPath()))
        else:
            yield (nodea.id, nodeb.id)

