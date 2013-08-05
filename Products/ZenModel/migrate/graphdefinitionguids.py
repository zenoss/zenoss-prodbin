##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

__doc__ = """
Graph definitions are stored in the zodb but we create a reference to them in the chart service.
The graph defs need guids so we are able to correlate the graph defs to the chart service
definitions.
"""

import logging
import Migrate

from Products.Zuul.interfaces import ICatalogTool
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from Products.ZenModel.GraphDefinition import GraphDefinition
from Products.ZenModel.GraphPoint import GraphPoint
log = logging.getLogger("zen.migrate")

class GraphDefinitionGuids(Migrate.Step):
    version = Migrate.Version(4, 9, 70)
    def __init__(self):
        Migrate.Step.__init__(self)

    def cutover(self, dmd):
        identifiables = [GraphDefinition, GraphPoint]
        catalog = dmd.global_catalog
        for brain in ICatalogTool(dmd).search(identifiables):
            try:
                obj = brain.getObject()
            except Exception:
                continue
            identifier = IGlobalIdentifier(obj)
            if not identifier.getGUID():
                guid = identifier.create()
                log.debug('Created guid for %s: %s', '/'.join(obj.getPrimaryPath()[3:]), guid)
                catalog.catalog_object(obj, idxs=(), update_metadata=True)


GraphDefinitionGuids()
