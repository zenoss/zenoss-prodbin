#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""RebuildRRDRelations

Rebuild Device relations for RRD refactor

$Id$"""

__version__ = "$Revision$"[11:-2]

from Acquisition import aq_base

import Migrate

class RebuildRRDRelations(Migrate.Step):
    version = 20.0

    def convert(self, dc):
        dc.buildRelations()
        if hasattr(aq_base(dc), "zCricketDeviceType"):
            dc._delProperty("zCricketDeviceType")
        if hasattr(aq_base(dc), "zCricketInterfaceIgnoreNames"):
            dc._delProperty("zCricketInterfaceIgnoreNames")
        if hasattr(aq_base(dc), "zCricketInterfaceIgnoreTypes"):
            dc._delProperty("zCricketInterfaceIgnoreTypes")
        if hasattr(aq_base(dc), "zCricketInterfaceMap"):
            dc._delProperty("zCricketInterfaceMap")


    def cutover(self, dmd):
        for dc in dmd.Devices.getSubOrganizers():
            #print dc.id
            self.convert(dc)
        self.convert(dmd.Devices)


RebuildRRDRelations()
