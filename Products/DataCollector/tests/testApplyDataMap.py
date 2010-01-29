###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import unittest
import Globals

from Products.DataCollector.ApplyDataMap import ApplyDataMap

class _dev(object):
    id = 'mydevid'
    def device(self): return self

class _obj(object):
    a = None
    b = None
    c = None
    id = 'myid'
    _device = None
    _dummy = None
    zCollectorDecoding = 'latin-1'
    def device(self):
        if not self._device:
            self._device = _dev()
        return self._device
    def _p_deactivate(self): pass
    _p_changed = False

ascii_objmap =  { 'a': 'abcdefg', 'b': 'hijklmn', 'c': 'opqrstu' }
utf8_objmap =   { 'a': u'\xe0'.encode('utf-8'), 
                  'b': u'\xe0'.encode('utf-8'), 
                  'c': u'\xe0'.encode('utf-8') } 
latin1_objmap = { 'a': u'\xe0'.encode('latin-1'), 
                  'b': u'\xe0'.encode('latin-1'), 
                  'c': u'\xe0'.encode('latin-1') }
utf16_objmap =  { 'a': u'\xff\xfeabcdef'.encode('utf-16'),
                  'b': u'\xff\xfexyzwow'.encode('utf-16'),
                  # "水z𝄞" (water, z, G clef), UTF-16 encoded, 
                  # little-endian with BOM
                  'c': '\xff\xfe\x34\x6c\x7a\x00\x34\xd8\x13\xdd' }

class ApplyDataMapTest(unittest.TestCase):

    def setUp(self):
        self.adm = ApplyDataMap()

    def test_updateObject_encoding(self):
        for enc in ('ascii', 'latin-1', 'utf-8', 'utf-16'):
            obj = _obj()
            obj.zCollectorDecoding = enc
            objmap = eval(enc.replace('-','')+'_objmap')
            self.adm._updateObject(obj, objmap)
            for key in objmap:
                self.assertEqual(getattr(obj, key), objmap[key].decode(enc))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(ApplyDataMapTest))
    return suite
