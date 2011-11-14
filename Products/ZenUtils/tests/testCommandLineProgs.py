###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import unittest
import subprocess

#  daemon, list of prefixes of expected output
_daemons = [
    ["zeneventserver", ["program running", "not running"]],
    ["zeneventd", ["program running", "not running"]],
    ["zopectl", ["program running", "daemon manager not running"]],
    ["zenhub", ["program running", "not running"]],
    ["zenjobs", ["program running", "not running"]],
    ["zenping", ["program running", "not running"]],
    ["zensyslog", ["program running", "not running"]],
    ["zenstatus", ["program running", "not running"]],
    ["zenactiond", ["program running", "not running"]],
    ["zentrap", ["program running", "not running"]],
    ["zenmodeler", ["program running", "not running"]],
    ["zenperfsnmp", ["program running", "not running"]],
    ["zencommand", ["program running", "not running"]],
    ["zenprocess", ["program running", "not running"]],
    ["zenrrdcached", ["program running", "not running"]],
    ["zenwin", ["program running", "not running"]],
    ["zeneventlog", ["program running", "not running"]],
]


def _startswithInList(testString, listToTest):
    """
    Checks each element in listToTest to see if any one of them
    starts with testString.
    """
    for e in listToTest:
        if testString.startswith(e):
            return True
    return False

class CmdLineProgs(unittest.TestCase):
    """Test the shipping command line tools and make sure they don't stack trace."""

    def testDaemons(self):
        for d, outputs in _daemons:
            daemon = subprocess.Popen([d, "status"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = daemon.communicate()
            cmd = out + err
            lines = cmd.splitlines(False)

            # look for stack traces, normal output is just one line
            msg = "%s status should return 1 line not %d" % (d, len(lines))
            self.assertEqual(len(lines), 1, msg)

            output = lines[0]
            msg = "%s status output: %r was not in expected list %r " % (d, output, outputs)
            self.assertEqual(_startswithInList(output, outputs), True, msg)

    def testZenpackCmd(self):
        
        cmd = subprocess.check_call(["zenpack", "--list"])
        self.assertEqual(cmd, 0, "zenpack --list should return 0 exit code; got %d" % cmd)    

def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(CmdLineProgs),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
