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

import Globals
import Migrate

import logging
from zope.event import notify
from Products.Zuul.catalog.events import IndexingEvent
from zExceptions import NotFound
log = logging.getLogger("zen.migrate")

class ReindexIpAddresses(Migrate.Step):
    version = Migrate.Version(3, 1, 70)

    def cutover(self, dmd):
        for x in dmd.global_catalog():
            try:
                notify(IndexingEvent(x.getObject(), ('ipAddress',)))
            except KeyError:
                log.warn("unable to find object %s, could not reindex" % x.getPath())
            except NotFound:
                pass
            

ReindexIpAddresses()
