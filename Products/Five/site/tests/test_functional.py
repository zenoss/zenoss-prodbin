##############################################################################
#
# Copyright (c) 2005 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Test local sites

$Id: test_functional.py 63112 2005-12-19 18:32:23Z philikon $
"""
import os, sys

if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

import pprint
from zope.app import zapi
from Products.Five import BrowserView
from Products.Five.site.interfaces import IFiveUtilityService
from Products.Five.site.localsite import FiveSiteManager
from Products.Five.site.tests.dummy import IDummyUtility

class CheckServicesView(BrowserView):

    def __call__(self):
        utility_service = zapi.getService(zapi.servicenames.Utilities)
        result = ('zapi.getServices() is zapi.getGlobalServices(): %s\n'
                  'IFiveUtilityService.providedBy(utility_service): %s\n'
                  'isinstance(zapi.getServices(), FiveSiteManager): %s\n'
                  % (zapi.getServices() is zapi.getGlobalServices(),
                     IFiveUtilityService.providedBy(utility_service),
                     isinstance(zapi.getServices(), FiveSiteManager)))
        return result

class LookupUtilitiesView(BrowserView):

    def __call__(self):
        dummy = getattr(self.context.utilities, IDummyUtility.getName())
        return "zapi.getUtility(IDummyUtility) == dummy: %s" % \
               (zapi.getUtility(IDummyUtility) == dummy)

def test_suite():
    from Testing.ZopeTestCase import FunctionalDocFileSuite
    return FunctionalDocFileSuite('functional.txt',
                                  package='Products.Five.site.tests')

if __name__ == '__main__':
    framework()
