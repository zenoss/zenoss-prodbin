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
""" Skins tool interface.

$Id: portal_skins.py 36457 2004-08-12 15:07:44Z jens $
"""

from Interface import Attribute
from Interface import Interface


class SkinsContainer(Interface):
    """ An object that provides skins.
    """

    def getSkinPath(name):
        """ Convert a skin name to a skin path.

        Permission -- Access contents information
        """

    def getDefaultSkin():
        """ Get the default skin name.

        Permission -- Access contents information
        """

    def getRequestVarname():
        """ Get the variable name to look for in the REQUEST.

        Permission -- Access contents information
        """

    def getSkinByPath(path, raise_exc=0):
        """ Get a skin at the given path.

        A skin path is of the format:
        'some/path, some/other/path, ...'  The first part has precedence.

        A skin is a specially wrapped object that looks through the layers
        in the correct order.

        Permission -- Python only
        """

    def getSkinByName(name):
        """ Get the named skin.

        Permission -- Python only
        """


class portal_skins(SkinsContainer):
    """ An object that provides skins to a portal object.
    """
    id = Attribute('id', 'Must be set to "portal_skins"')

    def getSkinSelections():
        """ Get the sorted list of available skin names.

        Permission -- Always available
        """
