###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from zope.interface import implements

from Products.ZenModel.interfaces import IIndexed
from ZenModelRM import ZenModelRM
from ZenPackable import ZenPackable

class MibBase(ZenModelRM, ZenPackable):
    implements(IIndexed)
    default_catalog = 'mibSearch'

    _relations = ZenPackable._relations[:]

    moduleName = ""
    nodetype = ""
    oid = ""
    status = ""
    description = ""

    _properties = (
        {'id':'moduleName', 'type':'string', 'mode':'w'},
        {'id':'nodetype', 'type':'string', 'mode':'w'},
        {'id':'oid', 'type':'string', 'mode':'w'},
        {'id':'status', 'type':'string', 'mode':'w'},
        {'id':'description', 'type':'string', 'mode':'w'},
    )


    def __init__(self, id, title="", **kwargs):
        super(ZenModelRM, self).__init__(id, title)
        atts = self.propertyIds()
        for key, val in kwargs.items():
            if key in atts: setattr(self, key, val)


    def getFullName(self):
        """Return full value name in form MODULE::attribute.
        """
        return "%s::%s" % (self.moduleName, self.id)

        
    def summary(self):
        """Return summary string for Mib objects.
        """
        return [str(getattr(self, p)) for p in self.propertyIds() \
                if str(getattr(self, p))]
    
