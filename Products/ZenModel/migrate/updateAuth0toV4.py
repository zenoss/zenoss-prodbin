##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__='''
This updates Auth0 plugin
'''

import logging

log = logging.getLogger("zen.migrate")

import Migrate
import re
from Products.ZenUtils.Auth0.Auth0 import setup, PLUGIN_VERSION, email_pattern
from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION



class UpdateAuth0toV4(Migrate.Step):

    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def cutover(self, dmd):
        setup(dmd)
        log.info("Auth0 version=%s is installed.", PLUGIN_VERSION)
        
        for us in dmd.ZenUsers.getAllUserSettings():
            if not getattr(us, 'email', '') and email_pattern.match(us.id):
                setattr(us, 'email', us.id)

UpdateAuth0toV4()
