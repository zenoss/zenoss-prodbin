#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Create standard_error_message at the root level of zope

'''

__version__ = "$Revision$"[11:-2]

import Migrate
import os

class BetterStandardErrorMessage(Migrate.Step):
    version = Migrate.Version(1, 1, 0)

    def cutover(self, dmd):
    	''' try/except to better handle access restrictions
    	'''
        app = dmd.getPhysicalRoot()
        if app.hasObject('standard_error_message'):
            app._delObject('standard_error_message')
        zenhome = os.getenv('ZENHOME')
        file = open('%s/Products/ZenModel/dtml/standard_error_message.dtml' %
                        zenhome)
        try:
            text = file.read()
        finally:
            file.close()
        import OFS.DTMLMethod
        OFS.DTMLMethod.addDTMLMethod(app, id='standard_error_message',
                                        file=text)

BetterStandardErrorMessage()
