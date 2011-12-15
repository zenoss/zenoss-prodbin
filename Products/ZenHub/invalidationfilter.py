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
import md5
import logging
from cStringIO import StringIO
from zope.interface import implements
from Products.ZenModel.DeviceClass import DeviceClass
from Products.Zuul.interfaces import ICatalogTool

from .interfaces import IInvalidationFilter, FILTER_EXCLUDE, FILTER_CONTINUE

log = logging.getLogger('zen.InvalidationFilter')


class DeviceClassInvalidationFilter(object):
    implements(IInvalidationFilter)

    iszorcustprop = re.compile("^[zc][A-Z]").search
    weight = 10

    def _updateDeviceClassChecksumMap(self, context):
        """
        Iterate over all device classes and generate a checksum.
        """
        root = context.dmd.Devices.primaryAq()
        brains = ICatalogTool(root).search(DeviceClass)
        results = {}
        for brain in brains:
            results[brain.getPath()] = self._deviceClassChecksum(brain.getObject())
        self.checksum_map = results

    def _deviceClassChecksum(self, devclass):
        """
        Generate a checksum representing the state of the device class as it
        pertains to configuration. This takes into account templates and
        zProperties, nothing more.
        """
        m = md5.new()
        s = StringIO()
        # Checksum includes all bound templates
        for tpl in devclass.getRRDTemplates():
            s.seek(0)
            s.truncate()
            # TODO: exportXml is a bit of a hack. Sorted, etc. would be better.
            tpl.exportXml(s)
            m.update(s.getvalue())
        # Checksum all zProperties and custom properties
        for zId in sorted(devclass.zenPropertyIds(pfilt=self.iszorcustprop)):
            m.update('%s|%s' % (zId, devclass.zenPropertyString(zId)))
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

























