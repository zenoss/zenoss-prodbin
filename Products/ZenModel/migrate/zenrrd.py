#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""RebuildRRDRelations

Rebuild Device relations for RRD refactor

$Id$"""

__version__ = "$Revision$"[11:-2]

import Migrate

class RebuildRRDRelations(Migrate.Step):
    version = 20.0

    def cutover(self, dmd):
        for dc in dmd.Devices.getSubOrganizers():
            dc.buildRelations()
        dmd.Devices.buildRelations()

RebuildRRDRelations()
