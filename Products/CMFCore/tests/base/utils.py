##############################################################################
#
# Copyright (c) 2002 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" CMF test utils.

$Id: utils.py 36457 2004-08-12 15:07:44Z jens $
"""

from unittest import TestSuite

from sys import modules


def build_test_suite(package_name, module_names, required=1,
                     suite_name='test_suite'):
    """
    Utlitity for building a test suite from a package name
    and a list of modules.

    If required is false, then ImportErrors will simply result
    in that module's tests not being added to the returned
    suite.
    """

    suite = TestSuite()
    try:
        for name in module_names:
            the_name = package_name+'.'+name
            __import__(the_name,globals(),locals())
            suite.addTest( getattr(modules[the_name], suite_name)() )
    except ImportError:
        if required:
            raise
    return suite

def has_path( catalog, path ):
    """
        Verify that catalog has an object at path.
    """
    if type( path ) is type( () ):
        path = '/'.join(path)
    rids = map( lambda x: x.data_record_id_, catalog.searchResults() )
    for rid in rids:
        if catalog.getpath( rid ) == path:
            return 1
    return 0
