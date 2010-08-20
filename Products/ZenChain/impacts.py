###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from nested_set import MultiTreeNestedSetItem
from Products.ZenUtils.orm import meta, nested_transaction

STATIC_LINK = 0

# Ignore this, still working on it

class ImpactRelationship(meta.Base, MultiTreeNestedSetItem):
    __tablename__ = 'impact'
    def __init__(self, **kwargs):
        if 'category' not in kwargs:
            kwargs['category'] = STATIC_LINK
        super(ImpactRelationship, self).__init__(**kwargs)

    def getLinkType(self):
        return self.category

    def setLinkType(self, value=STATIC_LINK):
        self.category = value

    linkType = property(getLinkType, setLinkType)
