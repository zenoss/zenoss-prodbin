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

__doc__ = '''

Fix templates for defect #7718

$Id:$
'''
import Migrate


class FixCorruptedGraphDefs(Migrate.Step):
    version = Migrate.Version(3, 0, 2)

    def cutover(self, dmd):
        for template in dmd.Devices.getAllRRDTemplates():
            for graphDef in template.graphDefs():
                self.zenfixit(graphDef)

    def zenfixit(self, graphDef):
        try:
            graphDef.miny = int(graph.miny)
        except:
            graphDef.miny = -1

        try:
            graphDef.maxy = int(graph.maxy)
        except:
            graphDef.maxy = -1


FixCorruptedGraphDefs()
