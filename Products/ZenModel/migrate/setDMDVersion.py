##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__='''

Set dmd.version for the maintenance release when zenmigrate runs as part of
upgrading the release.  This ensures that dmd.version is set when there are
no migrate scripts between minor versions.

'''
import Migrate


class setDMDVersion(Migrate.Step):
    version = Migrate.Version(5, 0, 70)

    def cutover(self, dmd):
        ''' no-op cutover needed for Migrate.Step '''

setDMDVersion()
