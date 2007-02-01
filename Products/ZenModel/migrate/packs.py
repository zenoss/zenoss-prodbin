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

class Packs(Migrate.Step):
    version = Migrate.Version(1, 2, 0)

    def cutover(self, dmd):
        dmd.buildRelations()

Packs()
