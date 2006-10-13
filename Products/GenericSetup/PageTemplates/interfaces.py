##############################################################################
#
# Copyright (c) 2005 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""PageTemplate interfaces.

$Id: interfaces.py 68406 2006-05-31 10:12:09Z yuppie $
"""

from zope.interface import Interface


class IZopePageTemplate(Interface):

    """Page Templates using TAL, TALES, and METAL.
    """

    def read():
        """Generate a text representation of the Template source.
        """

    def write(text):
        """Change the Template by parsing a read()-style source text.
        """
