#################################################################
#
#   Copyright (c) 2006 Zentinel Systems, Inc. All rights reserved.
#
#################################################################
import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

import unittest

from ZenModelBaseTest import ZenModelBaseTest


class TestEvents(ZenModelBaseTest):
    pass


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestEvents))
    return suite

if __name__=="__main__":
    framework()
