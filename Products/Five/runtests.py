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
"""Run tests

Run tests with the (temporarily) forked new-and-improved test runner
and supporting 'zope.testing' package, now located at
Products.Five.testing.

To run tests, use the ``zopectl`` script::

  $ bin/zopectl run Products/Five/runtests.py -v -s Products.Five

$Id: runtests.py 61015 2005-10-31 11:39:06Z philikon $
"""
import os, sys
from Products.Five.testing import testrunner

instance = os.path.abspath(
    os.path.join(os.path.split(sys.argv[0])[0], '..'))

defaults = [
    '--path', instance,
    '--path', '%s/lib/python' % instance,
    '--package', 'Products',
    '--tests-pattern', '^tests$',
    ]

sys.exit(testrunner.run(defaults))
