##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Build packs relationship on dmd

$Id:$
'''
import Migrate
log = Migrate.log

from Products.ZenModel.ZenPackable import ZenPackable

class Packs(Migrate.Step):
    version = Migrate.Version(2, 0, 0)

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
