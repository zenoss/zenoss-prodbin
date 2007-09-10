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
import Migrate

import Globals
from Products.ZenModel.MinMaxThreshold import MinMaxThreshold
from Products.ZenModel.ThresholdClass import ThresholdClass

import logging
log = logging.getLogger("zen.migrate")

class Thresholds(Migrate.Step):
    version = Migrate.Version(2, 1, 0)

    def replaceThreshold(self, template, old):
        if not isinstance(old, ThresholdClass):
            new = MinMaxThreshold(old.id)
            template.thresholds.removeRelation(old)
            for p in old._properties:
                name = p['id']
                setattr(new, name, getattr(old, name))
            old = new
        template.thresholds._setObject(old.id, old)

    def cutover(self, dmd):
        for t in dmd.Devices.getAllRRDTemplates():
            log.debug("Converting thresholds on %r", t)
            for old in t.thresholds():
                log.debug("   %r", old)
                self.replaceThreshold(t, old)

thresholds = Thresholds()
