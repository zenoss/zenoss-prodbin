##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""GenericSetup ZCML directives.

$Id: zcml.py 68512 2006-06-07 16:24:12Z yuppie $
"""

from zope.configuration.fields import GlobalObject
from zope.configuration.fields import MessageID
from zope.configuration.fields import Path
from zope.configuration.fields import PythonIdentifier
from zope.interface import Interface

from interfaces import BASE
from registry import _profile_registry


class IRegisterProfileDirective(Interface):

    """Register profiles with the global registry.
    """

    name = PythonIdentifier(
        title=u'Name',
        description=u'',
        required=True)

    title = MessageID(
        title=u'Title',
        description=u'',
        required=True)

    description = MessageID(
        title=u'Description',
        description=u'',
        required=True)

    directory = Path(
        title=u'Path',
        description=u"If not specified 'profiles/<name>' is used.",
        required=False)

    provides = GlobalObject(
        title=u'Type',
        description=u"If not specified 'BASE' is used.",
        default=BASE,
        required=False)

    for_ = GlobalObject(
        title=u'Site Interface',
        description=u'If not specified the profile is always available.',
        default=None,
        required=False)


_profile_regs = []
def registerProfile(_context, name, title, description, directory=None,
                    provides=BASE, for_=None):
    """ Add a new profile to the registry.
    """
    product = _context.package.__name__
    if directory is None:
        directory = 'profiles/%s' % name

    _profile_regs.append('%s:%s' % (product, name))

    _context.action(
        discriminator = ('registerProfile', product, name),
        callable = _profile_registry.registerProfile,
        args = (name, title, description, directory, product, provides, for_)
        )


def cleanUp():
    global _profile_regs
    for profile_id in _profile_regs:
        del _profile_registry._profile_info[profile_id]
        _profile_registry._profile_ids.remove(profile_id)
    _profile_regs = []

from zope.testing.cleanup import addCleanUp
addCleanUp(cleanUp)
del addCleanUp
