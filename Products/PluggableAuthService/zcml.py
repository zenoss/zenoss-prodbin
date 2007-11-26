##############################################################################
#
# Copyright (c) 2007 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""PAS ZCML directives.

$Id: zcml.py 72891 2007-02-27 18:24:41Z tseaver $
"""
from zope.configuration.fields import PythonIdentifier
from zope.interface import Interface

from PluggableAuthService import MultiPlugins
from PluggableAuthService import registerMultiPlugin as rMP


class IRegisterMultiPlugin(Interface):

    """Register profiles with the global registry.
    """

    class_ = PythonIdentifier(
        title=u'Class',
        description=u'',
        required=False)

    meta_type = PythonIdentifier(
        title=u'Meta-Type',
        description=u"If not specified, 'class/meta_type' is used.",
        required=False)


_mt_regs = []
def registerMultiPlugin(_context, class_=None, meta_type=None):
    """ Add a new meta_type to the registry.
    """
    if not class_ and not meta_type:
        raise ConfigurationError(
            "At least one of 'class' or 'meta_type' is required.")

    if not meta_type:
        meta_type = class_.meta_type

    _mt_regs.append(meta_type)

    _context.action(
        discriminator = ('registerMultiPlugin', meta_type),
        callable = rMP,
        args = (meta_type,),
        )


def cleanUp():
    global _mt_regs
    for meta_type in _mt_regs:
        MultiPlugins.remove(meta_type)
    _mt_regs = []

from zope.testing.cleanup import addCleanUp
addCleanUp(cleanUp)
del addCleanUp
