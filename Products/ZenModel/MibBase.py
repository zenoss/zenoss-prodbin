#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

from ZenModelRM import ZenModelRM

class MibBase(ZenModelRM):
    
    default_catalog = 'mibSearch'

    nodetype = ""
    oid = ""
    status = ""
    description = ""

    _properties = (
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

        
        
    def summary(self):
        """Return summary string for Mib objects.
        """
        return [str(getattr(self, p)) for p in self.propertyIds()]
    
    
    def manage_afterAdd(self, item, container):
        """setup relationshipmanager add object to index and build relations """
        if item == self: 
            self.index_object()


    def manage_afterClone(self, item):
        self.index_object()


    def manage_beforeDelete(self, item, container):
        if item == self or getattr(item, "_operation", -1) < 1: 
            ManagedEntity.manage_beforeDelete(self, item, container)
            self.unindex_object()


    def index_object(self):
        """interfaces use hostname + interface name as uid"""
        cat = getattr(self, self.default_catalog, None)
        if cat != None: 
            cat.catalog_object(self, self.getId())
            
                                                
    def unindex_object(self):
        """interfaces use hostname + interface name as uid"""
        cat = getattr(self, self.default_catalog, None)
        if cat != None: 
            cat.uncatalog_object(self.getId())


