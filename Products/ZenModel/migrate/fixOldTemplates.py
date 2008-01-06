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

Update existing templates to include fixes in r7650.

$Id:$
'''
import Migrate
import re

class FixOldTemplates(Migrate.Step):
    version = Migrate.Version(2, 1, 2)

    def cutover(self, dmd):
        for template in dmd.Devices.getAllRRDTemplates():
            if template.id == 'FileSystem':
                for graph in template.graphDefs():
                    if graph.id == 'Utilization':
                        self.fixFileSystemTemplates(graph)
                        continue

            for graph in template.graphDefs():
                if graph.id == 'Throughput':
                    self.fixIpInterfaceTemplates(graph)
                    continue


    def fixFileSystemTemplates(self, graph):
        if not graph.custom.startswith('CDEF:percent=usedBlocks'): return
        graph.custom = ''
        graph.miny = 0
        graph.maxy = 100
        for gp in graph.graphPoints():
            if gp.id != 'usedBlocks': continue
            gp.format = '%5.2lf%%'
            gp.legend = 'Used'
            gp.rpn = '${here/totalBlocks},/,100,*'


    def fixIpInterfaceTemplates(self, graph):
        if graph.custom: return
        if not re.search('bits', graph.units, re.I): return
        graph.units = 'bits/sec'
        graph.miny = 0
        for gp in graph.graphPoints():
            if not gp.id.endswith('Octets') or gp.rpn: continue
            gp.rpn = '8,*'
            if gp.id.endswith('InOctets'):
                gp.legend = 'Inbound'
            elif gp.id.endswith('OutOctets'):
                gp.legend = 'Outbound'


FixOldTemplates()
