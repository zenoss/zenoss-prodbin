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

Fix templates for defect #2719

$Id:$
'''
import Migrate

class FixOldTemplates_23(Migrate.Step):
    version = Migrate.Version(2, 3, 0)

    def cutover(self, dmd):
        for template in dmd.Devices.getAllRRDTemplates():
            for graph in template.graphDefs():
                if graph.id == 'Throughput':
                    self.fixIpInterfaceTemplates(graph)
                    continue

    def fixIpInterfaceTemplates(self, graph):
        if graph.custom: return
        for gp in graph.graphPoints():
            if gp.id.endswith('InOctets'):
                gp.legend = 'Inbound'
            elif gp.id.endswith('OutOctets'):
                gp.legend = 'Outbound'

FixOldTemplates_23()
