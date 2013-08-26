##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

__doc__ = """

"""

import logging
import Migrate

from Products.ZenModel.Authorization import manage_addAuthorization
log = logging.getLogger("zen.migrate")

class AddAuthorizationObject(Migrate.Step):
    version = Migrate.Version(4, 9, 70)
    def __init__(self):
        Migrate.Step.__init__(self)

    def cutover(self, dmd):
        app = dmd.unrestrictedTraverse('/')
        if app._getOb('authorization', None) is None:
            manage_addAuthorization(app)
            
AddAuthorizationObject()
