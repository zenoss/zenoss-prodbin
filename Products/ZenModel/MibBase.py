#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

from ZenModelRM import ZenModelRM

class MibBase(ZenModelRM):
    
    default_catalog = 'mibSearch'

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
        self.index_object()


    def manage_afterClone(self, item):
        self.index_object()


    def manage_beforeDelete(self, item, container):
        self.unindex_object()


    def index_object(self):
        """use MIB::name as index key.
        """
        if getattr(self, self.default_catalog, None) is not None:
            self.mibSearch.catalog_object(self, self.getPrimaryId())
            
                                                
    def unindex_object(self):
        """use MIB::name as index key.
        """
        if getattr(self, self.default_catalog, None) is not None:
            self.mibSearch.uncatalog_object(self.getPrimaryId())


