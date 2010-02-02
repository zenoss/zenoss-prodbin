###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from zope.interface import Interface
from zope.configuration.fields import GlobalObject
from zope.schema import TextLine

class IDirectRouter(Interface):
    """
    Registers a name and a javascript viewlet for a DirectRouter subclass.
    """
    name = TextLine(
        title=u"Name",
        description=u"The name of the requested view.")

    for_ = GlobalObject(
        title=u"For Interface",
        description=u"The interface the directive is used for.",
        required=False)

    class_ = GlobalObject(
        title=u"Class",
        description=u"The DirectRouter subclass"
    )

    namespace = TextLine(
        title=u"Namespace",
        description=unicode("The JavaScript namespace under which the"
                            " remote methods should be available"),
        required=False
    )

    layer = TextLine(
        title=u"Layer",
        description=u"The layer",
        required=False
    )

    timeout = TextLine(
        title=u"Timeout",
        description=unicode("Override the default timeout (in milliseconds)"
                            " for the calls"),
        required=False,
        default=u"30000"
    )
