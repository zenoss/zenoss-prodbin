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

from ZenModelRM import ZenModelRM
from ZenPackable import ZenPackable

class MibBase(ZenModelRM, ZenPackable):
    
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
    
    
    def manage_afterAdd(self, item, container):
        """
        Device only propagates afterAdd if it is the added object.
        """
        super(MibBase,self).manage_afterAdd(item, container)
        self.index_object()


    def manage_afterClone(self, item):
        """Not really sure when this is called."""
        super(MibBase,self).manage_afterClone(item)
        self.index_object()


    def manage_beforeDelete(self, item, container):
        """
        Device only propagates beforeDelete if we are being deleted or copied.
        Moving and renaming don't propagate.
        """
        super(MibBase,self).manage_beforeDelete(item, container)
        self.unindex_object()
