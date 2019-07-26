##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import Migrate

"""
Update zStatusEventClass zProperty from /Status/* to /Status/,
because Impact doesn't consider that * is a wildcard
"""


class UpdatezStatusEventClassProp(Migrate.Step):
    version = Migrate.Version(300, 0, 10)

    def cutover(self, dmd):
        if (hasattr(dmd.Devices, 'zStatusEventClass') and
                dmd.Devices.zStatusEventClass == '/Status/*'):
            dmd.Devices._updateProperty('zStatusEventClass', '/Status/')

UpdatezStatusEventClassProp()
