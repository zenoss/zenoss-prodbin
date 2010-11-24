###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import logging
import Migrate

from Products.Zuul.interfaces import ICatalogTool
from Products.ZenUtils.guid.interfaces import IGloballyIdentifiable, IGlobalIdentifier

log = logging.getLogger("zen.migrate")

class CreateMissingGuids(Migrate.Step):
    version = Migrate.Version(3, 1, 0)
    def __init__(self):
        Migrate.Step.__init__(self)

    def cutover(self, dmd):
        force = getattr(dmd, 'guid_table', None) is None

        log.debug('Creating GUIDs...')
        identifiables = [o.__name__ for o in IGloballyIdentifiable.dependents.keys()]
        for brain in ICatalogTool(dmd).search(identifiables):
            obj = brain.getObject()
            identifier = IGlobalIdentifier(obj)
            if force or not identifier.getGUID():
                guid = identifier.create(force)
                log.debug('Created guid for %s: %s', '/'.join(obj.getPrimaryPath()[3:]), guid)

CreateMissingGuids()