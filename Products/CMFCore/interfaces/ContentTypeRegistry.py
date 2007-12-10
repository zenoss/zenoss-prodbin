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
""" Putfactory registration tool interface.

$Id: ContentTypeRegistry.py 36457 2004-08-12 15:07:44Z jens $
"""

from Interface import Interface


class ContentTypeRegistryPredicate(Interface):
    """ Express a rule for matching a given name/typ/body.

    predicateWidget -- Return a snipped of HTML suitable for editing the
        predicate; the snippet should arrange for values to be marshalled by
        ZPublisher as a ':record', with the ID of the predicate as the name of
        the record.

    The registry will call the predictate's 'edit' method, passing the fields
    of the record.
    """

    def __call__(name, typ, body):
        """ Return true if the rule matches, else false. """

    def getTypeLabel():
        """ Return a human-readable label for the predicate type. """


class ContentTypeRegistry(Interface):
    """ Registry for rules which map PUT args to a CMF Type Object. """

    def findTypeName(name, typ, body):
        """\
        Perform a lookup over a collection of rules, returning the
        the Type object corresponding to name/typ/body.  Return None
        if no match found.
        """
