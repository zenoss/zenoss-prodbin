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

class StandardErrorMessage(Migrate.Step):
    version = Migrate.Version(0, 23, 0)

    def cutover(self, dmd):
    	''' Remove index_html and replace with a python script that will
    	    redirect to /zport/dmd/
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

StandardErrorMessage()
