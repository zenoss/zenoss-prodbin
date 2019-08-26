##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__='''
This updates Auth0 plugin
'''

import logging

import Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION

log = logging.getLogger("zen.migrate")

import Migrate
from Products.ZenUtils.Auth0.Auth0 import setup, PLUGIN_VERSION

class UpdateAuth0toV4(Migrate.Step):

    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def cutover(self, dmd):
        setup(dmd)
        log.info("Auth0 version=%s is installed.", PLUGIN_VERSION)

UpdateAuth0toV4()
