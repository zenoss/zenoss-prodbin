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
""" Backward compatibility;  see Products.CMFCore.permissions

$Id: CMFCorePermissions.py 37540 2005-07-29 15:37:26Z efge $
"""

from permissions import *

from warnings import warn

warn( "The module, 'Products.CMFCore.CMFCorePermissions' is a deprecated "
      "compatiblity alias for 'Products.CMFCore.permissions';  please use "
      "the new module instead.", DeprecationWarning, stacklevel=2)
