##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from Products.Zuul.catalog.interfaces import IModelCatalogTool

import Migrate

log = logging.getLogger("zen.migrate")


class SendOrganizersToZing(Migrate.Step):
    """Update all organizers' catalog entries so they can be sent to Zing."""

    version = Migrate.Version(300, 0, 13)

    def cutover(self, dmd):
        try:
            orgs = \
                dmd.Devices.getSubOrganizers() + \
                dmd.Groups.getSubOrganizers() + \
                dmd.Systems.getSubOrganizers() + \
                dmd.Locations.getSubOrganizers() + \
                dmd.ComponentGroups.getSubOrganizers()
        except Exception as e:
            logging.error("error getting list of organizers: %s", e)
            return

        for org in orgs:
            try:
                IModelCatalogTool(org).update(org)
            except Exception as e:
                logging.error("error updating catalog for organizers: %s", org.getOrganizerName())


SendOrganizersToZing()
