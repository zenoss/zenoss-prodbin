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
from itertools import imap
from zope.component import adapts, provideAdapter
from zope.interface import implements, Interface
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.Zuul.interfaces import IInfo
from Products import Zuul
from Products.Zuul import infos
class ITarget(Interface):
    pass


class Target(object):
    implements(ITarget)
    id = "Target"

    def __init__(self):
        self.foo = "foo"
        
    _properties = ( 
        {'id': 'foo', 'type':'int', 'mode':'w'},
        {'id': 'dummyProperty', 'type':'string', 'mode':'w', 'setter': 'setValue'}
       )
    def value(self):
        return 'value'
    
    def setValue(self, value):
        self._value = 'bar'

    def setDummyProperty(self, value):
        self._dummyProperty = value

    
        
class TargetInfo(infos.InfoBase):
    implements(IInfo)
    adapts(ITarget)
            
    @property
    def value(self):
        return self._obj.value()
    
    def dummyProperty(self):
        return 'foo'

    
class InfoTest(BaseTestCase):

    def setUp(self):
        super(InfoTest, self).setUp()
        provideAdapter(TargetInfo)
        target = Target()
        self.info = TargetInfo(target)


    def test_Zuuldotinfo(self):
        isinfo = lambda x:isinstance(x, TargetInfo)

        single = Zuul.info(Target())
        alist = Zuul.info([Target(), Target()])
        adict = Zuul.info({'a':Target(), 'b':Target()})
        nested = Zuul.info([{'a':[Target()], 'b':Target()}])

        self.assert_(isinfo(single))
        self.assert_(isinstance(alist, imap))
        for ob in alist:
            self.assert_(isinfo(ob))
        self.assert_(isinstance(adict, dict))
        for k, v in adict.items():
            self.assert_(isinfo(v))
        self.assert_(isinstance(nested, imap))
        
def test_suite():
    return unittest.TestSuite((unittest.makeSuite(InfoTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
