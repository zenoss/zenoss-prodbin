#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Create the directories on the file system necessary for importing and exporting
templates to and from Zenoss.

'''

__version__ = "$Revision$"[11:-2]

import os

import transaction

from Products.ZenModel.ZenossInfo import manage_addZenossInfo

import Migrate

zenhome = os.getenv('ZENHOME')

class AboutZenoss(Migrate.Step):
    version = 23.0

    def cutover(self, dmd):
        portal = dmd.getPhysicalRoot().zport
        manage_addZenossInfo(portal)
        transaction.commit()

AboutZenoss()
