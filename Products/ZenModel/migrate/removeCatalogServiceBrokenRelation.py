##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

import Migrate
from Products.ZenRelations.ToOneRelationship import ToOneRelationship

log = logging.getLogger('zen.migrate')


class RemoveCatalogServiceBrokenRelation(Migrate.Step):
    version = Migrate.Version(200, 0, 0)

    def cutover(self, dmd):
        for nodes in dmd.Processes.Zenoss.getChildNodes():
            if isinstance(nodes, ToOneRelationship):
                if nodes.pack.obj.id == "ZenPacks.zenoss.CatalogService":
                    try:
                        nodes.pack().packables.removeRelation()
                    except Exception as ex:
                        log.info("Can't remove relation for CatalogService, %s", ex)


RemoveCatalogServiceBrokenRelation()
