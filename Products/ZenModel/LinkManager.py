##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from itertools import groupby

from Acquisition import aq_base

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from OFS.Folder import Folder

from json import dumps
from Products.CMFCore.utils import getToolByName
from Products.ZCatalog.ZCatalog import manage_addZCatalog
from Products.ZenModel.Device import Device
from Products.ZenUtils.Search import makeCaseInsensitiveFieldIndex
from Products.ZenUtils.NetworkTree import NetworkLink
from Products.Zuul import getFacade
from Products.ZenEvents.events2.processing import Manager
from zenoss.protocols.protobufs.zep_pb2 import (SEVERITY_CRITICAL, SEVERITY_ERROR,
                                                SEVERITY_WARNING, SEVERITY_INFO,
                                                SEVERITY_DEBUG, SEVERITY_CLEAR)
from zenoss.protocols.protobufs.zep_pb2 import STATUS_NEW, STATUS_ACKNOWLEDGED

security = ClassSecurityInfo()

NODE_IDS = dict(
    layer_3 = {'IpNetwork':'networkId', 'Device':'deviceId'},
    layer_2 = {'LAN':'lanId', 'Device':'deviceId'}
)

def _getComplement(context, layer=3):
    key = 'layer_%d' % layer
    nodestuff = NODE_IDS[key]
    if not isinstance(context, basestring):
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


def _create_layer2_catalog(mgr):
    layer_2_indices = (
        ('lanId', makeCaseInsensitiveFieldIndex),
        ('macaddress', makeCaseInsensitiveFieldIndex),
        ('deviceId', makeCaseInsensitiveFieldIndex),
        ('interfaceId', makeCaseInsensitiveFieldIndex)
    )
    mgr._addLinkCatalog('layer2_catalog', layer_2_indices)


def _create_layer3_catalog(mgr):
    layer_3_indices = (
        ('networkId', makeCaseInsensitiveFieldIndex),
        ('ipAddressId', makeCaseInsensitiveFieldIndex),
        ('deviceId', makeCaseInsensitiveFieldIndex),
        ('interfaceId', makeCaseInsensitiveFieldIndex)
    )
    mgr._addLinkCatalog('layer3_catalog', layer_3_indices)


def _create_catalogs(mgr):
    _create_layer2_catalog(mgr)
    _create_layer3_catalog(mgr)


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
        self.zep = getFacade('zep', dmd)
        self.idmgr = Manager(dmd)

    def _getComponentUuid(self, devuuid, compid):
        try:
            dev = self.idmgr.getElementByUuid(devuuid)
            compuuid = self.idmgr.getElementUuidById(dev, Device, compid)
            return compuuid
        except Exception:
            return None

    def getStatus(self):
        brains = self.abrains + self.bbrains

        # lookup all device uuids, make sure at least one exists
        devUuids = [self.idmgr.findDeviceUuid(a.deviceId, None) for a in brains]
        validDevUuids = filter(None, devUuids)
        if not validDevUuids:
            return SEVERITY_CLEAR

        # if there is any open /Status/Ping event on any device, return CRITICAL severity
        statusPingFilter = self.zep.createEventFilter(
            tags = validDevUuids,
            event_class = '/Status/Ping/',
            status = (STATUS_NEW, STATUS_ACKNOWLEDGED),
            severity = (SEVERITY_WARNING, SEVERITY_ERROR, SEVERITY_CRITICAL)
        )
        maxpingrec = self.zep.getEventSummaries(0, filter=statusPingFilter, sort=(('count','desc'),), limit=1)
        if maxpingrec and maxpingrec['total'] > 0:
            return SEVERITY_CRITICAL

        # no /Status/Ping events found, just return worst severity of all events on all interface components
        devCompPairs = zip(devUuids, (a.interfaceId for a in brains))
        compUuids = (self._getComponentUuid(devuuid, compid)
                        for devuuid, compid in devCompPairs
                        if devuuid is not None)
        components = filter(None, compUuids)
        if components:
            sev = self.zep.getWorstSeverity(components)
            return sev

        return SEVERITY_CLEAR

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
        locpaths.reverse() # otherwise the "startswith" call gets too eager
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
            if getattr(self.dmd.unrestrictedTraverse(k), 'zDrawMapLinks', True):
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
        result = set()
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
        result = set()
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
