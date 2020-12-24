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


import Migrate

log = logging.getLogger("zen.migrate")


class ResendComponentOrganizersToZing(Migrate.Step):
    """Cause all organizer fields on devices and their components to be re-sent
    to Zing"""

    version = Migrate.Version(300, 0, 13)

    def cutover(self, dmd):
        zing_handler = zope.component.createObject("ZingObjectUpdateHandler", dmd)
        for device in dmd.Devices.getSubDevices():
            zing_handler.update_object(device, ['path'])


ResendComponentOrganizersToZing()
