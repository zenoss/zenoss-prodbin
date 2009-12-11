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

from zope.interface import implements
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.Zuul.interfaces import IInfo
from Products.Zuul.decorators import decorator, marshalto, marshal

class Child(object):
    implements(IInfo)
    x = '67890'
    notx = 'I should not be included'

class Something(object):
    implements(IInfo)
    x = '12345'
    hithere = "I am a banana!"
    def abcde(self):
        return {'a':Child(), 'b':[1, Child()]}
    
@decorator
def reverse(f, *args, **kwargs):
    result = f(*args, **kwargs)
    return result[::-1]

class DecoratorTest(BaseTestCase):
    
    def test_decoratordecorator(self):
        @reverse
        def test():
            "A docstring"
            return "ABCDE"
        self.assertEqual(test.__name__, 'test')
        self.assertEqual(test.__doc__, 'A docstring')
        self.assertEqual(test(), 'EDCBA')
    
    def test_marshalto(self):
        @marshalto(['x', 'abcde'])
        def test():
            return Something()
        result = test()
        self.assert_(isinstance(result, dict))
        self.assertEqual(sorted(result.keys()), ['abcde', 'x'])
        self.assertEqual(result['abcde']['a'].keys(), ['x'])
    
    def test_marshal(self):
        @marshal
        def test():
            return Something()
        result = test()
        self.assert_(isinstance(result, dict))
        self.assertEqual(sorted(result.keys()), ['hithere', 'x'])

def test_suite():
    return unittest.TestSuite((unittest.makeSuite(DecoratorTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')