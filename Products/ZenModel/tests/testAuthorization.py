#############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

import time

from Products.ZenModel.Authorization import *

from ZenModelBaseTest import ZenModelBaseTest

class temp_folder:
    def __init__(self):
        self.session_data  = {}

class TestAuthorization(ZenModelBaseTest):

    def afterSetUp(self):
        super(TestAuthorization, self).afterSetUp()
        self.auth = self.dmd.authorization
        self.auth.temp_folder = temp_folder()

    def testGetTokenIsNone(self):
        self.assertIsNone( self.auth.getToken( "XXX"))

    def testCreateaAndGetToken(self):
        token = self.auth.createToken( 1, 1, time.time() + 120)
        self.assertIs( token, self.auth.getToken( 1))

    def testTokenExpired(self):
        token = self.auth.createToken( 1, 1, 0)
        self.assertTrue( self.auth.tokenExpired( 1))
        self.assertIsNone( self.auth.getToken( 1))

