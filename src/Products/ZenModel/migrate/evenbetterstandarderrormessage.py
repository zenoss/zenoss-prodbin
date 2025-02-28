##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Create standard_error_message at the root level of zope

'''

import Migrate
from Products.ZenUtils.Utils import zenPath

class EvenBetterStandardErrorMessage(Migrate.Step):
    version = Migrate.Version(2, 0, 0)

    def cutover(self, dmd):
        ''' try/except to better handle access restrictions
        '''
        app = dmd.getPhysicalRoot()
        if app.hasObject('standard_error_message'):
            app._delObject('standard_error_message')
        file = open(zenPath('Products/ZenModel/dtml/standard_error_message.dtml'))
        try:
            text = file.read()
        finally:
            file.close()
        import OFS.DTMLMethod
        OFS.DTMLMethod.addDTMLMethod(app, id='standard_error_message',
                                        file=text)

EvenBetterStandardErrorMessage()
