###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from zope.interface import Attribute, Interface

class IReportableFactory(Interface):
    def exports():
        """
        return an iterable of IReportables adapting the context
        """

class IReportable(Interface):
    id = Attribute("Identifier of the represented object (usually path)")
    uid = Attribute("The path in the object graph to the object")
    entity_class_name = Attribute("The name of the entity class, to be used" \
            + " when generating reporting schemas")

    def reportProperties():
        """
        get column values for entity. this is a list of tuples, where each
        contains the id, type, and value of the property
        """

class IReportableSubscriber(IReportable):
    """
    This type of IReportable is called from a factory that expects to get
    a list of subscribers.  In order to differentiate between a subscriber
    intended for factory A rather than from factory B, a factoryId is used.
    """
    zenpack = Attribute("ZenPack in which this subscriber lives.")
    factoryId = Attribute("Value used by factory to search for applicable reportables.")
