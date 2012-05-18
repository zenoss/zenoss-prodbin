###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__="""
File systems windows file systems use their mount as the name of the component but they
are indexed under titleOrId (which is their id).
"""

import Migrate
import logging
from zope.event import notify
from Products.ZenModel.FileSystem import FileSystem
from Products.Zuul.interfaces import ICatalogTool
from Products.Zuul.catalog.events import IndexingEvent
log = logging.getLogger('zen.migrate')

class FileSystemIndexName(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        for brain in ICatalogTool(dmd).search(FileSystem):
            try:
                filesystem = brain.getObject()
                notify(IndexingEvent(filesystem, idxs=('name',)))
            except:
                log.warn("Unable to reindex %s", brain.getPath())

FileSystemIndexName()
