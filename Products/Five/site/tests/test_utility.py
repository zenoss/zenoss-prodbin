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

$Id: test_utility.py 60963 2005-10-30 06:34:38Z philikon $
"""
import os, sys

if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

import unittest
import sets
from Testing import ZopeTestCase

from zope.interface import directlyProvides
from zope.component.exceptions import ComponentLookupError
from zope.component.service import serviceManager
from zope.component.servicenames import Utilities
from zope.app import zapi
from zope.app.tests.placelesssetup import setUp, tearDown
from zope.app.component.hooks import setSite

import Products.Five
from Products.Five import zcml
from Products.Five.site.interfaces import IRegisterUtilitySimply
from Products.Five.site.localsite import enableLocalSiteHook
from Products.Five.site.tests.dummy import manage_addDummySite, \
     IDummyUtility, ISuperDummyUtility, DummyUtility

class LocalUtilityServiceTest(ZopeTestCase.ZopeTestCase):

    def afterSetUp(self):
        setUp()
        zcml.load_config("meta.zcml", Products.Five)
        zcml.load_config("permissions.zcml", Products.Five)
        zcml.load_config("configure.zcml", Products.Five.site)
        zcml_text = """\
        <five:localsite
            xmlns:five="http://namespaces.zope.org/five"
            class="Products.Five.site.tests.dummy.DummySite" />"""
        zcml.load_string(zcml_text)
        manage_addDummySite(self.folder, 'site')
        enableLocalSiteHook(self.folder.site)
        setSite(self.folder.site)

    def beforeTearDown(self):
        tearDown()

    def test_getServicesHook(self):
        from Products.Five.site.localsite import FiveSiteManager
        from Products.Five.site.utility import SimpleLocalUtilityService

        local_sm = zapi.getServices(None)
        self.failIf(local_sm is serviceManager)
        self.failUnless(isinstance(local_sm, FiveSiteManager))

        local_sm = zapi.getServices(self.folder.site)
        self.failIf(local_sm is serviceManager)
        self.failUnless(isinstance(local_sm, FiveSiteManager))

        utils = zapi.getService(Utilities)
        self.failUnless(isinstance(utils, SimpleLocalUtilityService))

    def test_getUtilitiesNoUtilitiesFolder(self):
        utils = zapi.getService(Utilities)
        #XXX test whether utils really is a local utility service...
        self.assertRaises(ComponentLookupError, utils.getUtility, IDummyUtility)
        self.assertEquals(list(utils.getUtilitiesFor(IDummyUtility)), [])
        self.assertEquals(list(utils.getAllUtilitiesRegisteredFor(IDummyUtility)), [])

    def test_registerUtilityOnUtilityService(self):
        utils = zapi.getService(Utilities)
        dummy = DummyUtility()
        utils.registerUtility(IDummyUtility, dummy, 'dummy')

        self.assertEquals(zapi.getUtility(IDummyUtility, name='dummy'), dummy)
        self.assertEquals(list(zapi.getUtilitiesFor(IDummyUtility)), 
                          [('dummy', dummy)])
        self.assertEquals(list(zapi.getAllUtilitiesRegisteredFor(
            IDummyUtility)), [dummy])

    def test_registerUtilityOnSiteManager(self):
        sm = zapi.getServices()
        self.failUnless(IRegisterUtilitySimply.providedBy(sm))
        dummy = DummyUtility()
        sm.registerUtility(IDummyUtility, dummy, 'dummy')

        self.assertEquals(zapi.getUtility(IDummyUtility, name='dummy'), dummy)
        self.assertEquals(list(zapi.getUtilitiesFor(IDummyUtility)), 
                          [('dummy', dummy)])
        self.assertEquals(list(zapi.getAllUtilitiesRegisteredFor(
            IDummyUtility)), [dummy])

    def test_registerTwoUtilitiesWithSameNameDifferentInterface(self):
        sm = zapi.getServices()
        self.failUnless(IRegisterUtilitySimply.providedBy(sm))
        dummy = DummyUtility()
        superdummy = DummyUtility()
        directlyProvides(superdummy, ISuperDummyUtility)
        sm.registerUtility(IDummyUtility, dummy, 'dummy')
        sm.registerUtility(ISuperDummyUtility, superdummy, 'dummy')

        self.assertEquals(zapi.getUtility(IDummyUtility, 'dummy'), dummy)
        self.assertEquals(zapi.getUtility(ISuperDummyUtility, 'dummy'),
                          superdummy)

    def test_nestedSitesDontConflictButStillAcquire(self):
        # let's register a dummy utility in the dummy site
        dummy = DummyUtility()
        sm = zapi.getServices()
        sm.registerUtility(IDummyUtility, dummy)

        # let's also create a subsite and make that our site
        manage_addDummySite(self.folder.site, 'subsite')
        enableLocalSiteHook(self.folder.site.subsite)
        setSite(self.folder.site.subsite)

        # we should still be able to lookup the original utility from
        # the site one level above
        self.assertEqual(zapi.getUtility(IDummyUtility), dummy)

        # now we register a dummy utility in the subsite and see that
        # its registration doesn't conflict
        subdummy = DummyUtility()
        sm = zapi.getServices()
        sm.registerUtility(IDummyUtility, subdummy)

        # when we look it up we get the more local one now because the
        # more local one shadows the less local one
        self.assertEqual(zapi.getUtility(IDummyUtility), subdummy)

        # getAllUtilitiesFor gives us both the more local and the less
        # local utility (XXX not sure if this is the right semantics
        # for getAllUtilitiesFor)
        self.assertEqual(sets.Set(zapi.getAllUtilitiesRegisteredFor(IDummyUtility)),
                         sets.Set([subdummy, dummy]))

        # getUtilitiesFor will only find one, because the more local
        # one shadows the less local one
        self.assertEqual(list(zapi.getUtilitiesFor(IDummyUtility)),
                         [('', subdummy)])

    def test_registeringTwiceIsConflict(self):
        dummy1 = DummyUtility()
        dummy2 = DummyUtility()
        sm = zapi.getServices()
        sm.registerUtility(IDummyUtility, dummy1)
        self.assertRaises(ValueError, sm.registerUtility,
                          IDummyUtility, dummy2)

        sm.registerUtility(IDummyUtility, dummy1, 'dummy')
        self.assertRaises(ValueError, sm.registerUtility,
                          IDummyUtility, dummy2, 'dummy')

    def test_utilitiesHaveProperAcquisitionContext(self):
        dummy = DummyUtility()
        sm = zapi.getServices()
        sm.registerUtility(IDummyUtility, dummy)

        # let's see if we can acquire something all the way from the
        # root (Application) object; we need to be careful to choose
        # something that's only available from the root object
        from Acquisition import aq_acquire
        dummy = zapi.getUtility(IDummyUtility)
        acquired = aq_acquire(dummy, 'ZopeAttributionButton', None)
        self.failUnless(acquired is not None)

        name, dummy = zapi.getUtilitiesFor(IDummyUtility).next()
        acquired = aq_acquire(dummy, 'ZopeAttributionButton', None)
        self.failUnless(acquired is not None)

        dummy = zapi.getAllUtilitiesRegisteredFor(IDummyUtility).next()
        acquired = aq_acquire(dummy, 'ZopeAttributionButton', None)
        self.failUnless(acquired is not None)        

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(LocalUtilityServiceTest))
    return suite

if __name__ == '__main__':
    framework()
