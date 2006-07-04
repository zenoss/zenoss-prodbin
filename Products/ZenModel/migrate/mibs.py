#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Add Mibs organizer and friends.

'''

__version__ = "$Revision$"[11:-2]

from Acquisition import aq_base

import Migrate
import os

class Mibs(Migrate.Step):
    version = 22.0

    def cutover(self, dmd):
        if hasattr(dmd, 'Mibs'):
            return

        import Zope2
        Zope2.configure(os.path.join(os.environ['ZENHOME'], "etc/zope.conf"))
        app = Zope2.app()
        zdmd = app.zport.dmd

        from Products.ZenModel.MibOrganizer import manage_addMibOrganizer
        manage_addMibOrganizer(zdmd, 'Mibs')

Mibs()
