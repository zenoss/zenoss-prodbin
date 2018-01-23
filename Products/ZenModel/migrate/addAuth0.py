##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''
This migration script adds Auth0 plugin to PAS.
''' 

import logging
from Products.ZenModel.ZMigrateVersion import (
    SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION
)
log = logging.getLogger("zen.migrate")

import Migrate
from Products.ZenUtils.Auth0 import setup


class AddAuth0(Migrate.Step):

    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def cutover(self, dmd):
        setup(dmd)
        log.info("Auth0 is installed.")

AddAuth0()
