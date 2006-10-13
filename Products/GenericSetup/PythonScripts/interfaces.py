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
"""PythonScripts interfaces.

$Id: interfaces.py 40314 2005-11-22 13:21:47Z yuppie $
"""

from zope.interface import Interface


class IPythonScript(Interface):

    """Web-callable scripts written in a safe subset of Python.

    The function may include standard python code, so long as it does not
    attempt to use the "exec" statement or certain restricted builtins.
    """

    def read():
        """Generate a text representation of the Script source.

        Includes specially formatted comment lines for parameters, bindings
        and the title.
        """

    def write(text):
        """Change the Script by parsing a read()-style source text.
        """
