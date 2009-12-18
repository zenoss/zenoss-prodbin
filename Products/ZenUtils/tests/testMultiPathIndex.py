###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
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

from Products.ZenUtils.MultiPathIndex import MultiPathIndex

class Dummy:

    meta_type="foo"

    def __init__( self, path):
        self.path = path

    def __str__( self ):
        return '<Dummy: %s>' % self.path

    __repr__ = __str__


class MultiPathIndexTests(unittest.TestCase):
    """ Test MultiPathIndex objects """

    def setUp(self):
        self._index = MultiPathIndex( 'path' )
        self._values = {
          1 : Dummy("/aa/aa/aa/1.html"),
          2 : Dummy("/aa/aa/bb/2.html"),
          3 : Dummy("/aa/aa/cc/3.html"),
          4 : Dummy("/aa/bb/aa/4.html"),
          5 : Dummy("/aa/bb/bb/5.html"),
          6 : Dummy("/aa/bb/cc/6.html"),
          7 : Dummy("/aa/cc/aa/7.html"),
          8 : Dummy("/aa/cc/bb/8.html"),
          9 : Dummy("/aa/cc/cc/9.html"),
          10 : Dummy("/bb/aa/aa/10.html"),
          11 : Dummy("/bb/aa/bb/11.html"),
          12 : Dummy("/bb/aa/cc/12.html"),
          13 : Dummy("/bb/bb/aa/13.html"),
          14 : Dummy("/bb/bb/bb/14.html"),
          15 : Dummy("/bb/bb/cc/15.html"),
          16 : Dummy("/bb/cc/aa/16.html"),
          17 : Dummy("/bb/cc/bb/17.html"),
          18 : Dummy("/bb/cc/cc/18.html"),
          19 : Dummy(["/bb/cc/cc/19.html",
                     "/aa/cc/cc/19.html"])
        }

    def _populateIndex(self):
        for k, v in self._values.items():
            self._index.index_object( k, v )

    def testEmpty(self):
        self.assertEqual(self._index.numObjects() ,0)
        self.assertEqual(self._index.getEntryForObject(1234), None)
        self._index.unindex_object( 1234 ) # nothrow
        self.assertEqual(self._index._apply_index({"suxpath":"xxx"}), None)

    def testUnIndex(self):
        self._populateIndex()
        self.assertEqual(self._index.numObjects(), 19)

        for k in self._values.keys():
            self._index.unindex_object(k)

        self.assertEqual(self._index.numObjects(), 0)
        self.assertEqual(len(self._index._index), 0)
        self.assertEqual(len(self._index._unindex), 0)

    def testReindex(self):
        self._populateIndex()
        self.assertEqual(self._index.numObjects(), 19)

        o = Dummy('/foo/bar')
        self._index.index_object(20, o)
        self.assertEqual(self._index.numObjects(), 20)
        self._index.index_object(20, o)
        self.assertEqual(self._index.numObjects(), 20)

    def testUnIndexError(self):
        self._populateIndex()
        # this should not raise an error
        self._index.unindex_object(-1)

        # nor should this
        self._index._unindex[1] = "/broken/thing"
        self._index.unindex_object(1)

    def testRoot(self):

        self._populateIndex()
        tests = ( ("/",0, range(1,20)), )

        for comp,level,results in tests:
            for path in [comp,"/"+comp,"/"+comp+"/"]:
                res = self._index._apply_index(
                                    {"path":{'query':path,"level":level}})
                lst = list(res[0].keys())
                self.assertEqual(lst,results)

        for comp,level,results in tests:
            for path in [comp,"/"+comp,"/"+comp+"/"]:
                res = self._index._apply_index(
                                    {"path":{'query':( (path,level),)}})
                lst = list(res[0].keys())
                self.assertEqual(lst,results)

    def testSimpleTests(self):

        self._populateIndex()
        tests = [
            ("aa", 0, [1,2,3,4,5,6,7,8,9,19]),
            ("aa", 1, [1,2,3,10,11,12] ),
            ("bb", 0, [10,11,12,13,14,15,16,17,18,19]),
            ("bb", 1, [4,5,6,13,14,15] ),
            ("bb/cc", 0, [16,17,18,19] ),
            ("bb/cc", 1, [6,15] ),
            ("bb/aa", 0, [10,11,12] ),
            ("bb/aa", 1, [4,13] ),
            ("aa/cc", -1, [3,7,8,9,12,19] ),
            ("bb/bb", -1, [5,13,14,15] ),
            ("18.html", 3, [18] ),
            ("18.html", -1, [18] ),
            ("cc/18.html", -1, [18] ),
            ("cc/18.html", 2, [18] ),
        ]

        for comp,level,results in tests:
            for path in [comp,"/"+comp,"/"+comp+"/"]:
                res = self._index._apply_index(
                                    {"path":{'query':path,"level":level}})
                lst = list(res[0].keys())
                self.assertEqual(lst,results)

        for comp,level,results in tests:
            for path in [comp,"/"+comp,"/"+comp+"/"]:
                res = self._index._apply_index(
                                    {"path":{'query':( (path,level),)}})
                lst = list(res[0].keys())
                self.assertEqual(lst,results)

    def testComplexOrTests(self):

        self._populateIndex()
        tests = [
            (['aa','bb'],1,[1,2,3,4,5,6,10,11,12,13,14,15]),
            (['aa','bb','xx'],1,[1,2,3,4,5,6,10,11,12,13,14,15]),
            ([('cc',1),('cc',2)],0,[3,6,7,8,9,12,15,16,17,18,19]),
        ]

        for lst ,level,results in tests:

            res = self._index._apply_index(
                            {"path":{'query':lst,"level":level,"operator":"or"}})
            lst = list(res[0].keys())
            self.assertEqual(lst,results)

    def testComplexANDTests(self):

        self._populateIndex()
        tests = [
            (['aa','bb'],1,[]),
            ([('aa',0),('bb',1)],0,[4,5,6]),
            ([('aa',0),('cc',2)],0,[3,6,9,19]),
        ]

        for lst ,level,results in tests:
            res = self._index._apply_index(
                            {"path":{'query':lst,"level":level,"operator":"and"}})
            lst = list(res[0].keys())
            self.assertEqual(lst,results)

    def testQueryPathReturnedInResult(self):

        index = self._index
        index.index_object(1, Dummy("/ff"))
        index.index_object(2, Dummy("/ff/gg"))
        index.index_object(3, Dummy("/ff/gg/3.html"))
        index.index_object(4, Dummy("/ff/gg/4.html"))
        res = index._apply_index({'path': {'query': '/ff/gg'}})
        lst = list(res[0].keys())
        self.assertEqual(lst, [2, 3, 4])
    
    def testAddingPathsIndividually(self):
        index = self._index
        index.index_object(1, Dummy("/ff"))
        index.index_object(2, Dummy("/ff/gg"))
        index.index_object(3, Dummy("/ff/gg/3.html"))
        index.index_object(4, Dummy("/ff/gg/4.html"))
        index.index_paths(4, ('/aa/bb/4.html','/ff'))
        res1 = index._apply_index({'path': {'query': '/aa/bb'}})
        res2 = index._apply_index({'path': {'query': '/ff/gg'}})
        res3 = index._apply_index({'path': {'query': '/ff'}})
        self.assertEqual(list(res1[0].keys()), [4]);
        self.assertEqual(list(res2[0].keys()), [2, 3, 4]);
        self.assertEqual(list(res3[0].keys()), [1, 2, 3, 4]);

        res = index._apply_index({'path': {'query': '/', 'depth':1}})
        self.assertEqual(list(res[0].keys()), [1, 4]);
        res = index._apply_index({'path': {'query': '/ff', 'depth':0}})
        self.assertEqual(list(res[0].keys()), [4]);
        res = index._apply_index({'path': {'query': '/ff', 'depth':1}})
        self.assertEqual(list(res[0].keys()), [2]);
        res = index._apply_index({'path': {'query': '/ff', 'depth':2}})
        self.assertEqual(list(res[0].keys()), [2, 3, 4]);

    def testUnindexIndividualPaths(self):
        index = self._index
        index.index_object(1, Dummy("/ff"))
        index.index_paths(1, ('/a/b/c', '/a/b/b'))
        index.unindex_paths(1, ('/a/b/c',))
        res = index._apply_index({'path':{'query':'/a/b/c'}})[0].keys()
        self.assertEqual(list(res), [])
        res = index._apply_index({'path':{'query':'/a/b/b'}})[0].keys()
        self.assertEqual(list(res), [1])
        res = index._apply_index({'path':{'query':'/ff'}})[0].keys()
        self.assertEqual(list(res), [1])

    def testUnindexIndividualPathError(self):
        index = self._index
        index.index_object(1, Dummy("/ff"))
        # This should not throw an error
        index.unindex_paths(1, ('/a/b/c',))
        


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(MultiPathIndexTests),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
