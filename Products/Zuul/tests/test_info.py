###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import unittest

from zope.component import adapts, provideAdapter
from zope.interface import implements, Interface
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.Zuul.interfaces import IInfo
from Products import Zuul

class ITarget(Interface):
    pass

class Target(object):
    implements(ITarget)
    def value(self):
        return 'value'

class TargetInfo(object):
    implements(IInfo)
    adapts(ITarget)
    def __init__(self, obj):
        self._obj = obj
    @property
    def value(self):
        return self._obj.value()


class InfoTest(BaseTestCase):

    def setUp(self):
        super(InfoTest, self).setUp()
        provideAdapter(TargetInfo)

    def test_Zuuldotinfo(self):
        isinfo = lambda x:isinstance(x, TargetInfo)

        single = Zuul.info(Target())
        alist = Zuul.info([Target(), Target()])
        adict = Zuul.info({'a':Target(), 'b':Target()})
        nested = Zuul.info([{'a':[Target()], 'b':Target()}])

        self.assert_(isinfo(single))
        self.assert_(isinstance(alist, list))
        for ob in alist:
            self.assert_(isinfo(ob))
        self.assert_(isinstance(adict, dict))
        for k, v in adict.items():
            self.assert_(isinfo(v))
        self.assert_(isinstance(nested, list))
        self.assert_(isinfo(nested[0]['a'][0]))
        self.assert_(isinfo(nested[0]['b']))
        
    

        
def test_suite():
    return unittest.TestSuite((unittest.makeSuite(InfoTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')