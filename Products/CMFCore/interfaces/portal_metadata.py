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
""" Metadata registration tool interface.

$Id: portal_metadata.py 38328 2005-09-06 22:20:35Z tseaver $
"""

from Interface import Attribute
from Interface import Interface


class portal_metadata(Interface):
    """
        CMF metadata policies interface.
    """
    id = Attribute('id', 'Must be set to "portal_metadata"')

    #
    #   Site-wide queries, specific to Dublin Core metadata.
    #
    def getFullName(userid):
        """ Convert an internal userid to a "formal" name.
        
        o Convert only if possible, perhaps using the 'portal_membership'
          tool;  otherwise, return 'userid'.

        o Used to map userid's for Creator, Contributor DCMI queries.
        """

    def getPublisher():
        """ Return the "formal" name of the publisher of the site.
        """

    #
    #   Content-specific queries, for Dublin Core metadata.
    #
    def listAllowedSubjects(content=None):
        """ List the allowed values of the 'Subject' DCMI element.

        o 'Subject' elements should be keywords categorizing their resource.

        o Return only values appropriate for content's type, or all values
          if content is None.
        """

    def listAllowedFormats(content=None):
        """ List the allowed values of the 'Format' DCMI element.

        o These items should be usable as HTTP 'Content-type' values.

        o Return only values appropriate for content's type, or all values
          if content is None.
        """

    def listAllowedLanguages(content=None):
        """ List the allowed values of the 'Language' DCMI element.

        o 'Language' element values should be suitable for generating
          HTTP headers.

        o Return only values appropriate for content's type, or all values if
          content is None.
        """

    def listAllowedRights(content=None):
        """ List the allowed values of the 'Rights' DCMI element.

        o The 'Rights' element describes copyright or other IP declarations
          pertaining to a resource.

        o Return only values appropriate for content's type, or all values if
          content is None.
        """

    #
    #   Validation policy hooks.
    #
    def setInitialMetadata(content):
        """ Set initial values for content metatdata.
        
        o Supply any site-specific defaults.
        """

    def validateMetadata(content):
        """ Enforce portal-wide policies about metadata.
        
        o E.g., policies may require non-empty title/description, etc.
        
        o This method may be called by view / workflow code at "appropriate"
          times, such as immediately before saving changes to the metadata of
          an object.
        """
