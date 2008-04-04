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

from sets import Set as set
from itertools import groupby

from simplejson import dumps
from Acquisition import aq_base

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from OFS.Folder import Folder

from Products.CMFCore.utils import getToolByName
from Products.ZCatalog.ZCatalog import manage_addZCatalog
from Products.ZenUtils.Search import makeCaseInsensitiveFieldIndex
from Products.ZenUtils.NetworkTree import NetworkLink

security = ClassSecurityInfo()

NODE_IDS = dict(
    layer_3 = {'IpNetwork':'networkId', 'Device':'deviceId'}
)

def allcombos(items):
    results = []
    items.pop
    

def _getComplement(context, layer=3):
    key = 'layer_%d' % layer
    nodestuff = NODE_IDS[key]
    if not type(context)==type(""):
        try:
            context = nodestuff[context.meta_type]
        except KeyError:
            return None
    first, second = nodestuff.values()
    if context==first: 
        return second
    else:
        return first

def manage_addLinkManager(context, id="ZenLinkManager"):
    """ Make a LinkManager """
    mgr = LinkManager(id)
    context._setObject(mgr.id, mgr)
    mgr = context._getOb(id)
    _create_catalogs(mgr)

def _create_catalogs(mgr):
    # Layer 3
    layer_3_indices = (
        ('networkId', makeCaseInsensitiveFieldIndex),
        ('ipAddressId', makeCaseInsensitiveFieldIndex),
        ('deviceId', makeCaseInsensitiveFieldIndex),
        ('interfaceId', makeCaseInsensitiveFieldIndex)
    )
    mgr._addLinkCatalog('layer3_catalog', layer_3_indices)


class Layer3Link(object):
    """
    Provides an API for navigating paired groups of brains.
    """
    def __init__(self, dmd, twokeydict):
        a, b = twokeydict.items()
        aid, self.abrains = a
        bid, self.bbrains = b
        self.a = dmd.unrestrictedTraverse(aid)
        self.b = dmd.unrestrictedTraverse(bid)
        self.zem = dmd.ZenEventManager


    def getStatus(self):
        brains = self.abrains + self.bbrains
        comps =(
            dict(device=a.deviceId, component=a.interfaceId) for a in brains)
        sev, count = self.zem.getBatchComponentInfo(comps)
        if count: 
            return 5
        else:
            try:
                return int(sev)
            except:
                return 0

    def getAddresses(self):
        return (self.a.address, self.b.address)


class LinkManager(Folder):
    """ 
    A tool that keeps track of OSI layer links between objects.
    """
    def __init__(self, id, *args, **kwargs):
        Folder.__init__(self, id, *args, **kwargs)
        self.id = id

    def _getCatalog(self, layer=3):
        try: 
            return getToolByName(self, 'layer%d_catalog' % layer)
        except AttributeError:
            return None

    def _addLinkCatalog(self, id, indices):
        manage_addZCatalog(self, id, id)
        zcat = self._getOb(id)
        cat = zcat._catalog
        for index, factory in indices:
            cat.addIndex(index, factory(index))
            zcat.addColumn(index)

    def getLinkedNodes(self, meta_type, id, layer=3, visited=None):
        cat = self._getCatalog(layer)
        col = NODE_IDS['layer_%d' % layer][meta_type]
        nextcol = _getComplement(col, layer)
        brains = cat(**{col:id})
        gen1ids = set(getattr(brain, nextcol) for brain in brains)
        if visited:
            gen1ids = gen1ids - visited # Don't go places we've been!
        gen2 = cat(**{nextcol:list(gen1ids)})
        return gen2, gen1ids

    def getChildLinks(self, organizer):
        catalog = getToolByName(self.dmd.Devices, 'deviceSearch')
        result = {}
        locs = organizer.children()
        locpaths = ['/'.join(loc.getPrimaryPath()) for loc in locs]
        path = '/'.join(organizer.getPhysicalPath())
        subdevs = catalog(path=path)
        subids = dict((x.id, x.path) for x in subdevs)

        def _whichorg(brain):
            for path in locpaths:
                try:
                    brainpath = subids[brain.deviceId]
                except KeyError:
                    return '__outside'
                if filter(lambda x:'/'.join(x).startswith(path), brainpath): 
                    return path
            return '__outside'

        def _whichnet(brain):
            return brain.networkId

        def _whichdev(brain):
            return brain.deviceId

        links, nets = self.getLinkedNodes('Device', subids.keys())
        links = map(aq_base, links) # For comparison, can't be ImplicitAcq

        byloc = {}
        for k, g in groupby(links, _whichorg):
            byloc.setdefault(k, []).extend(g)
        if '__outside' in byloc: del byloc['__outside']

        bynet = {}
        for k, g in groupby(links, _whichnet):
            bynet.setdefault(k, []).extend(g)

        final = {}
        linkobs = []

        inverted_loc = {}
        for loc in byloc:
            for dev in byloc[loc]:
                inverted_loc[dev.deviceId] = loc
        for net in bynet:
            devs = bynet[net]
            alllocs = set()
            for dev in devs:
                if dev.deviceId and dev.deviceId in inverted_loc:
                    alllocs.add(inverted_loc[dev.deviceId])
            if len(alllocs)>=2:
                for dev in devs:
                    if dev.deviceId:
                        loc = inverted_loc.get(dev.deviceId, None)
                        if loc:
                            final.setdefault(loc, []).append(dev)
        def haslink(locs1, locs2):
            for l in locs1:
                for b in locs2:
                    if l.networkId==b.networkId: 
                        return True
        locs = final.keys()
        while locs:
            loc = locs.pop()
            for loc2 in locs:
                first = final[loc]
                second = final[loc2]
                if haslink(first, second):
                    link = Layer3Link(self.dmd, {loc:first, loc2:second})
                    linkobs.append(link)
        return dumps([(x.getAddresses(), x.getStatus()) for x in linkobs])

    def getChildLinks_recursive(self, context):
        """ Returns all links under a given Organizer, aggregated """
        result = set([])
        severities = {}
        links = self.getNetworkLinks(context)
        for x in links:
            geomapdata = x.getGeomapData(context)
            severities[geomapdata] = max(
                x.getStatus(),
                severities.get(geomapdata, 0)
            ) 
            result.add(geomapdata)
        addresses = [x for x in list(result) if x]
        severities = [severities[x] for x in addresses]
        return map(list, zip(map(list, addresses), severities))

    def getNetworkLinks(self, context):
        """
        An alternate way to get links under an Organizer.
        """
        result = set([])
        networks = filter(lambda x:x.zDrawMapLinks, 
                          self.dmd.Networks.getSubNetworks())
        siblings = [x.getPrimaryId() for x in context.children()]
        for net in networks:
            locdict = {}
            def addToDict(iface):
                loc = iface.device().location()
                if not loc: return
                here = loc.getPrimaryId()
                matched = False
                for sib in siblings:
                    if here.startswith(sib):
                        locdict.setdefault(sib, []).append(iface)
                        matched = True
                        break
                if not matched: 
                    locdict.setdefault(here, []).append(iface)
            for ip in net.ipaddresses.objectValuesGen():
                iface = ip.interface()
                if iface: addToDict(iface)
            if len(locdict)<=1: continue
            locgroups = locdict.values()
            while locgroups:
                lg = locgroups.pop()
                targets = []
                for g in locgroups: targets.extend(g)
                for l in lg:
                    for t in targets:
                        n = NetworkLink()
                        n.setEndpoints(l, t)
                        result.add(n)
        return result
InitializeClass(LinkManager)






