###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import re
from hashlib import md5
import logging
from cStringIO import StringIO
from zope.interface import implements
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.IpAddress import IpAddress
from Products.ZenModel.IpNetwork import IpNetwork
from Products.Zuul.interfaces import ICatalogTool

from twisted.internet import reactor, task
from twisted.internet.defer import inlineCallbacks

from .interfaces import IInvalidationFilter, FILTER_EXCLUDE, FILTER_CONTINUE

log = logging.getLogger('zen.InvalidationFilter')

# adjust this to higher values to include checksum initialization 
# of deeper levels of DeviceClass during zenhub startup
DEVICE_CLASS_HIERARCHY_INIT_CUTOFF = 5

def divideWhere(seq, cond):
    """
    Divide seq into items that match cond and items that don't.
    """
    t_items,f_items = [],[]
    for item in seq:
        if cond(item):
            t_items.append(item)
        else:
            f_items.append(item)
    return t_items,f_items

class IpInvalidationFilter(object):
    implements(IInvalidationFilter)

    weight = 1

    def initialize(self, context):
        pass

    def include(self, obj):
        if isinstance(obj, IpAddress) or isinstance(obj, IpNetwork):
            return FILTER_EXCLUDE
        return FILTER_CONTINUE

class DeviceClassInvalidationFilter(object):
    implements(IInvalidationFilter)

    iszorcustprop = re.compile("^[zc][A-Z]").search
    weight = 10

    @inlineCallbacks
    def _updateRemainingClassChecksums(self, brains):
        for pathlen,brain in brains:
            objpath = brain.getPath()
            if objpath not in self.checksum_map:
                log.debug("Initializing device class checksum for %s (deferred)", objpath)
                self.checksum_map[objpath] = self._deviceClassChecksum(brain.getObject())
                yield task.deferLater(reactor, 0, lambda : None)
        
    def _updateDeviceClassChecksumMap(self, context):
        """
        Iterate over all device classes and generate a checksum.
        """
        root = context.dmd.Devices.primaryAq()
        brains = ICatalogTool(root).search(DeviceClass)
        orderedBrains = sorted(((b.getPath().count('/'), b) for b in brains),
                               key=lambda x: x[0])
        highlevel,remaining = divideWhere(orderedBrains, 
                                          lambda x: x[0] <= DEVICE_CLASS_HIERARCHY_INIT_CUTOFF)
        results = {}
        for pathlen,brain in highlevel:
            objpath = brain.getPath()
            log.debug("Initializing device class checksum for %s", objpath)
            results[objpath] = self._deviceClassChecksum(brain.getObject())
        self.checksum_map = results
        
        # submit remaining class checksums to be computed during reactor free time
        reactor.callWhenRunning(self._updateRemainingClassChecksums, remaining)

    def _deviceClassChecksum(self, devclass):
        """
        Generate a checksum representing the state of the device class as it
        pertains to configuration. This takes into account templates and
        zProperties, nothing more.
        """
        m = md5()
        s = StringIO()
        # Checksum includes all bound templates
        for tpl in devclass.rrdTemplates():
            s.seek(0)
            s.truncate()
            # TODO: exportXml is a bit of a hack. Sorted, etc. would be better.
            tpl.exportXml(s)
            m.update(s.getvalue())
        # Checksum all zProperties and custom properties
        for zId in sorted(devclass.zenPropertyIds(pfilt=self.iszorcustprop)):
            if devclass.zenPropIsPassword(zId):
                propertyString = devclass.getProperty(zId, '')
            else:
                propertyString = devclass.zenPropertyString(zId)
            m.update('%s|%s' % (zId, propertyString))
        # Return the final checksum
        return m.hexdigest()

    def initialize(self, context):
        self._updateDeviceClassChecksumMap(context)

    def include(self, obj):
        # Move on if it's not a device class
        if not isinstance(obj, DeviceClass):
            return FILTER_CONTINUE

        # Checksum the device class
        current_checksum = self._deviceClassChecksum(obj)
        devclass_path = '/'.join(obj.getPrimaryPath())

        # Get what we have right now and compare
        existing_checksum = self.checksum_map.get(devclass_path, None)
        if current_checksum != existing_checksum:
            log.debug('%r has a new checksum! Including.' % obj)
            self.checksum_map[devclass_path] = current_checksum
            return FILTER_CONTINUE
        log.debug('%r checksum unchanged. Skipping.' % obj)
        return FILTER_EXCLUDE
