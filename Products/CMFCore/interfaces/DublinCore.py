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
""" Dublin Core interface.

$Id: DublinCore.py 36613 2004-10-12 09:22:52Z yuppie $
"""

from Interface import Interface


class DublinCore(Interface):
    """ Dublin Core metadata elements supported by CMF and their semantics.
    """

    def Title():
        """ Dublin Core Title element - resource name.

        Permission -- View

        Returns -- String
        """

    def listCreators():
        """ List Dublin Core Creator elements - resource authors.

        Depending on the implementation, this returns the full name(s) of the
        author(s) of the content object or their ids.

        Permission -- View

        Returns -- Sequence of strings
        """

    def Creator():
        """ Dublin Core Creator element - resource author.

        The first Dublin Core Creator element or an empty string.

        Permission -- View

        Returns -- String
        """

    def Subject():
        """ Dublin Core Subject element - resource keywords.

        Return zero or more keywords associated with the content object.

        Permission -- View

        Returns -- Sequence of strings
        """

    def Description():
        """ Dublin Core Description element - resource summary.

        Return a natural language description of this object.

        Permission -- View

        Returns -- String
        """

    def Publisher():
        """ Dublin Core Publisher element - resource publisher.

        Return full formal name of the entity or person responsible for
        publishing the resource.

        Permission -- View

        Returns -- String
        """

    def listContributors():
        """ Dublin Core Contributor elements - resource collaborators.

        Return zero or additional collaborators.

        Permission -- View

        Returns -- Sequence of strings
        """

    def Contributors():
        """ Deprecated alias of listContributors.

        'initial caps' names are reserved for strings.
        """

    def Date():
        """ Dublin Core Date element - default date.

        Permission -- View

        Returns -- String, formatted 'YYYY-MM-DD H24:MN:SS TZ'
        """

    def CreationDate():
        """ Dublin Core Date element - date resource created.

        Permission -- View

        Returns -- String, formatted 'YYYY-MM-DD H24:MN:SS TZ'
        """

    def EffectiveDate():
        """ Dublin Core Date element - date resource becomes effective.

        Permission -- View

        Returns -- String, formatted 'YYYY-MM-DD H24:MN:SS TZ'
        """

    def ExpirationDate():
        """ Dublin Core Date element - date resource expires.

        Permission -- View

        Returns -- String, formatted 'YYYY-MM-DD H24:MN:SS TZ'
        """

    def ModificationDate():
        """ Dublin Core Date element - date resource last modified.

        Permission -- View

        Returns -- String, formatted 'YYYY-MM-DD H24:MN:SS TZ'
        """

    def Type():
        """ Dublin Core Type element - resource type.

        Return a human-readable type name for the resource (perhaps mapped
        from its Zope meta_type).

        Permission -- View

        Returns -- String
        """

    def Format():
        """ Dublin Core Format element - resource format.

        Return the resource's MIME type (e.g. 'text/html', 'image/png', etc.).

        Permission -- View

        Returns -- String
        """

    def Identifier():
        """ Dublin Core Identifier element - resource ID.

        Returns unique ID (a URL) for the resource.

        Permission -- View

        Returns -- String
        """

    def Language():
        """ Dublin Core Language element - resource language.

        Return the RFC language code (e.g. 'en-US', 'pt-BR') for the resource.

        Permission -- View

        Returns -- String
        """

    def Rights():
        """ Dublin Core Rights element - resource copyright.

        Return a string describing the intellectual property status, if any,
        of the resource.

        Permission -- View

        Returns -- String
        """


class CatalogableDublinCore(Interface):
    """ Provide Zope-internal date objects for cataloging purposes.
    """

    def created():
        """ Dublin Core Date element - date resource created.

        Permission -- View

        Returns -- DateTime
        """

    def effective():
        """ Dublin Core Date element - date resource becomes effective.

        Permission -- View

        Returns -- DateTime
        """

    def expires():
        """ Dublin Core Date element - date resource expires.

        Permission -- View

        Returns -- DateTime
        """

    def modified():
        """ Dublin Core Date element - date resource last modified.

        Permission -- View

        Returns -- DateTime
        """


class MutableDublinCore(Interface):
    """ Update interface for mutable metadata.
    """

    def setTitle(title):
        """ Set Dublin Core Title element - resource name.

        Permission -- Modify portal content
        """

    def setCreators(creators):
        """ Set Dublin Core Creator elements - resource authors.

        Permission -- Modify portal content
        """

    def setSubject(subject):
        """ Set Dublin Core Subject element - resource keywords.

        Permission -- Modify portal content
        """

    def setDescription(description):
        """ Set Dublin Core Description element - resource summary.

        Permission -- Modify portal content
        """

    def setContributors(contributors):
        """ Set Dublin Core Contributor elements - resource collaborators.

        Permission -- Modify portal content
        """

    def setEffectiveDate(effective_date):
        """ Set Dublin Core Date element - date resource becomes effective.

        Permission -- Modify portal content
        """

    def setExpirationDate(expiration_date):
        """ Set Dublin Core Date element - date resource expires.

        Permission -- Modify portal content
        """

    def setFormat(format):
        """ Set Dublin Core Format element - resource format.

        Permission -- Modify portal content
        """

    def setLanguage(language):
        """ Set Dublin Core Language element - resource language.

        Permission -- Modify portal content
        """

    def setRights(rights):
        """ Set Dublin Core Rights element - resource copyright.

        Permission -- Modify portal content
        """
