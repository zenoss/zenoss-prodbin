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

__doc__='''

Build packs relationship on dmd

$Id:$
'''
import Migrate
log = Migrate.log

from Products.ZenModel.ZenPackable import ZenPackable

class Packs(Migrate.Step):
    version = Migrate.Version(1, 2, 0)

    def cutover(self, dmd):
        def recurse(obj):
            try:
                path = obj.getPrimaryUrlPath()
                if obj.getPrimaryUrlPath() not in ('/zport/dmd/Devices',
                                                   '/zport/dmd/Networks'):
                    log.debug(path)
                    if isinstance(obj, ZenPackable):
                        obj.buildRelations()
                    for child in obj.objectValues():
                        recurse(child)
            except Exception, ex:
                log.debug("Exception building relations: %s", ex)
        recurse(dmd)

Packs()
