##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

import zope.component

from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION  # noqa: E501

import Migrate

log = logging.getLogger("zen.migrate")


class ResendComponentOrganizersToZing(Migrate.Step):
    """Cause all organizer fields on devices and their components to be re-sent
    to Zing"""

    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def cutover(self, dmd):
        zing_handler = zope.component.createObject("ZingObjectUpdateHandler", dmd)
        for device in dmd.Devices.getSubDevices():
            zing_handler.update_object(device, ['path'])


ResendComponentOrganizersToZing()
