##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" Caching policies tool interface.

$Id: CachingPolicyManager.py 36457 2004-08-12 15:07:44Z jens $
"""

from Interface import Attribute
from Interface import Interface


class CachingPolicyManager(Interface):
    """
        Manage HTTP cache policies for skin methods.
    """
    id = Attribute( 'id', 'Must be set to "caching_policy_manager"' )

    def getHTTPCachingHeaders( content, view_method, keywords, time=None ):
        """
            Update HTTP caching headers in REQUEST based on 'content',
            'view_method', and 'keywords'.

            If 'time' is supplied, use it instead of the current time
            (for reliable testing).
        """
