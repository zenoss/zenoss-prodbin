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

log = logging.getLogger("zen.migrate")

import Migrate
from Products.ZenUtils.Auth0.Auth0 import setup


class AddAuth0(Migrate.Step):

    version = Migrate.Version(300, 0, 1)

    def cutover(self, dmd):
        setup(dmd)
        log.info("Auth0 is installed.")

AddAuth0()
