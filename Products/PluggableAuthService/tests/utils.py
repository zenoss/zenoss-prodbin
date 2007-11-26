##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors. All Rights
# Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this
# distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" PluggableAuthService unit tests utils

$Id: utils.py 70850 2006-10-20 18:44:07Z jens $
"""

def _setUpDefaultTraversable():
    # Work around behavior change in Zope 2.10 due to its use of the 
    # Zope 3 pagetemplates
    try:
        from zope.interface import Interface
        from zope.component import provideAdapter
        from zope.traversing.interfaces import ITraversable
        from zope.traversing.adapters import DefaultTraversable
        provideAdapter(DefaultTraversable, (Interface,), ITraversable)
    except ImportError:
        # Zope < 2.10 - no need to do anything
        pass
