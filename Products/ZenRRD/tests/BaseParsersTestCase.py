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
    Create data points for a ComponentCommandParser from a mapping of expected
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


def createPoints(expected):
    """
    Create data points for a CommandParser from a mapping of expected
    values.
    """
    if not isinstance(expected.values()[0], dict):
        return createSimplePoints(expected)
    
    points = []
    
    for componentScanValue in expected:
        data = dict(componentScanValue=componentScanValue)
        for id in expected[componentScanValue]:
            point = Object()
            point.id = id
            point.data = data
            point.expected = expected[componentScanValue][id]
            points.append(point)
            
    return points


class BaseParsersTestCase(BaseTestCase):

    def _testParser(self, parserMap, datadir, filename):

        # read the data file
        datafile = open('%s/%s' % (datadir, filename))
        command = datafile.readline().rstrip("\n")
        output = "".join(datafile.readlines())
        datafile.close()
        
        # read the file containing the expected values
        expectedfile = open('%s/%s.py' % (datadir, filename))
        expected = eval("".join(expectedfile.readlines()))
        expectedfile.close()
        
        cmd = Object()
        cmd.points = createPoints(expected)
        cmd.result = Object()
        cmd.result.output = output
        results = ParsedResults()
        Parser = parserMap.get(command)

        if Parser:
            parser = Parser()
        else:
            self.fail("No parser for %s" % command)
        
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
        
        def filenames():
            for entry in os.listdir(datadir):
                if (not entry.startswith(".") and \
                    not entry.endswith(".py") and
                    entry.find('~') == -1 and
                    entry.find('#') == -1):
                    yield entry
        
        counter = 0
        
        for filename in filenames():
            counter += self._testParser(parserMap, datadir, filename)
            
        self.assert_(counter > 0, counter)
        print "testParsers made", counter, "assertions."
