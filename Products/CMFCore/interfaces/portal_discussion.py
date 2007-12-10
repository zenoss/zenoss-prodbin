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
""" Discussion tool interface.

$Id: portal_discussion.py 36457 2004-08-12 15:07:44Z jens $
"""

from Interface import Attribute
from Interface import Interface


class oldstyle_portal_discussion(Interface):
    """ Links content to discussions.
    """
    id = Attribute('id', 'Must be set to "portal_discussion"')

    def getDiscussionFor(content):
        """ Get DiscussionItemContainer for content, create it if necessary.

        Permission -- Always available

        Returns -- DiscussionItemContainer object
        """

    def isDiscussionAllowedFor(content):
        """ Get boolean indicating whether discussion is allowed for content.

        This may be looked up via an object-specific value, or by place, or
        from a site-wide policy.

        Permission -- Always available

        Returns -- Boolean value
        """


class portal_discussion(oldstyle_portal_discussion):
    """ Links content to discussions.
    """

    def overrideDiscussionFor(content, allowDiscussion):
        """ Override discussability for the given object or clear the setting.

        If 'allowDiscussion' is None, then clear any overridden setting for
        discussability, letting the site's default policy apply.  Otherwise,
        set the override to match the boolean equivalent of 'allowDiscussion'.

        Permission -- Always available
        """
