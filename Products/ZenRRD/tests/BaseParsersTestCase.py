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


import os
from pprint import pformat

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenRRD.CommandParser import ParsedResults


class Object(object): 
    
    def __repr__(self):
        return pformat(dict([(attr, getattr(self, attr)) for attr in dir(self) 
                if not attr.startswith('__')]))


def createSimplePoints(expected):
    """
    Create data points for a CommandParser from a mapping of expected
    values.  These points are simple datapoints on the device,
    not a subcomponent.
    """
    points = []
    
    for key, value in expected.items():
        point = Object()
        point.id = key
        point.expected = value
        points.append(point)
    return points
    
    
class Context(object):
    """
    A fake context object for CommandParser.dataForParser() calls.  Pass in a
    key to the initializer and access to any attribute on this object will
    return that key.
    """
    
    def __init__(self, key):
        self.key = key
        
    def __getattr__(self, name):
        return self.key
        
        
def createPoints(expected, parser):
    """
    Create data points for a ComponentCommandParser from a mapping of expected
    values.
    """
    if not isinstance(expected.values()[0], dict):
        return createSimplePoints(expected)
    
    points = []
    
    for key in expected:
        
        for id in expected[key]:
            point = Object()
            point.id = id
            point.data = parser.dataForParser(Context(key), None)
            point.expected = expected[key][id]
            points.append(point)
            
    return points


def filenames(datadir):
    """recursively find and yield data-file filenames starting at datadir"""    
    
    for root, subFolders, files in os.walk(datadir):
        
        if root.find(".svn") == -1:
            
            for entry in files:
                
                if (not entry.startswith(".") and
                    not entry.endswith(".py") and
                    not entry.endswith(".pyc") and
                    entry.find('~') == -1 and
                    entry.find('#') == -1):
                    
                    yield os.path.join(root, entry)


class BaseParsersTestCase(BaseTestCase):

    def _testParser(self, parserMap, filename):

        # read the data file
        datafile = open(filename)
        command = datafile.readline().rstrip("\n")
        output = "".join(datafile.readlines())
        datafile.close()
        
        # read the file containing the expected values
        expectedfile = open('%s.py' % (filename,))
        expected = eval("".join(expectedfile.readlines()))
        expectedfile.close()
        
        results = ParsedResults()
        Parser = parserMap.get(command)
        
        if Parser:
            parser = Parser()
        else:
            self.fail("No parser for %s" % command)
        
        cmd = Object()
        cmd.points = createPoints(expected, parser)
        cmd.result = Object()
        cmd.result.output = output
        
        parser.processResults(cmd, results)
        
        self.assertEqual(len(cmd.points), len(results.values),
            "%s expected %s values, actual %s" % (filename, len(cmd.points), 
            len(results.values)))
        
        counter = 0
        
        for value in results.values:
            self.assertEqual(value[0].expected, value[1])
            counter += 1
            
        return counter


    def _testParsers(self, datadir, parserMap):
        """
        Test all of the parsers that have test data files in the data
        directory.
        """
        counter = 0
        
        for filename in filenames(datadir):
            counter += self._testParser(parserMap, filename)
            
        self.assert_(counter > 0, counter)
        print "testParsers made", counter, "assertions."
