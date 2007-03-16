#################################################################
#
#   Copyright (c) 2007 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Build packs relationship on dmd

$Id:$
'''
import Migrate
log = Migrate.log

class Packs(Migrate.Step):
    version = Migrate.Version(1, 2, 0)

    def cutover(self, dmd):
        def recurse(obj):
            log.debug(obj.getPrimaryUrlPath())
            try:
                obj.buildRelations()
            except AttributeError:
                pass
            for child in obj.objectValues():
                recurse(child)
        recurse(dmd)

Packs()
