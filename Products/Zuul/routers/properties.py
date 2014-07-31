##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.ZenUtils.Ext import DirectResponse
from Products.ZenUtils.jsonutils import unjson
from Products.ZenModel.ZenossSecurity import ZEN_ZPROPERTIES_EDIT
from Products import Zuul
from Products.Zuul.decorators import contextRequire, serviceConnectionError
from Products.ZenMessaging.audit import audit
from Products.ZenUtils.Ext import DirectRouter

class PropertiesRouter(DirectRouter): 

    def _getFacade(self):
        return Zuul.getFacade('properties', self.context)
                
    def _filterData(self, params, data):
        """
        @param params: params passed to the caller and used here for filtering
        @param data: data to be filtered and returned
        """
        # filter
        if params:
            if isinstance(params, basestring):
                filters = unjson(params)
            else:
                filters = params
            def hasFilter(row, key, value):
                if row.get(key) is not None:
                    return value.lower() in str(row.get(key)).lower()

            for key, value in filters.iteritems():
                # assume AND for sorting
                data = [row for row in data if hasFilter(row, key, value)]
               
        return data   
           
    def _sortData(self, sort, data, dir): 
        """
        @param data: data to be sorted and returned
        """
        reverse = False
        if dir != 'ASC':
            reverse = True
        return sorted(data,  key=lambda row: row[sort], reverse=reverse)          

    @serviceConnectionError
    def getZenProperties(self, uid, start=0, params="{}", limit=None, sort=None,
                         page=None, dir='ASC'):
        """
        Returns the definition and values of all
        the zen properties for this context
        @type  uid: string
        @param uid: unique identifier of an object
        """
        facade = self._getFacade()
        data = facade.getZenProperties(uid, exclusionList=('zCollectorPlugins', 'zCredentialsZProperties'))
        
        data = self._filterData(params, data)
        if sort:
            data = self._sortData(sort, data, dir)

        return DirectResponse(data=Zuul.marshal(data), totalCount=len(data))
            
    @serviceConnectionError
    def getZenProperty(self, uid, zProperty):
        """
        Returns information about a zproperty for a
        given context, including its value
        @rtype:   Dictionary
        @return:  B{Properties}:
             - path: (string) where the property is defined
             - type: (string) type of zproperty it is
             - options: (Array) available options for the zproperty
             - value (Array) value of the zproperty
             - valueAsString (string)
        """
        facade = self._getFacade()
        data = facade.getZenProperty(uid, zProperty)
        return DirectResponse.succeed(data=Zuul.marshal(data))      
        
    @serviceConnectionError
    def getCustomProperties(self, uid, start=0, params="{}", limit=None, sort=None,
                         page=None, dir='ASC'):
        """
        Returns the definition and values of all
        the zen properties for this context
        @type  uid: string
        @param uid: unique identifier of an object
        """
        facade = self._getFacade()
        data = facade.getCustomProperties(uid)
        
        data = self._filterData(params, data)
        if sort:
            data = self._sortData(sort, data, dir)            

        return DirectResponse(data=Zuul.marshal(data), totalCount=len(data))   
        
    def addCustomProperty(self, id, value, label, uid, type):
        """
        adds a new property to the / of the tree
        """    
        facade = self._getFacade()
        facade.addCustomProperty(id, value, label, uid, type)
        return DirectResponse.succeed(msg="Property %s added successfully." % (id))

    @serviceConnectionError
    @contextRequire(ZEN_ZPROPERTIES_EDIT, 'uid') 
    def setZenProperty(self, uid, zProperty, value):
        """
        Sets the zProperty value.
        @type  uid: string
        @param uid: unique identifier of an object
        @type  zProperty: string or dictionary
        @param zProperty: either a string that represents which zproperty we are changing or 
        key value pair dictionary that is the list of zproperties we wish to change.
        @type  value: anything
        @param value: if we are modifying a single zproperty then it is the value, it is not used
        if a dictionary is passed in for zProperty

        """
        facade = self._getFacade()
        properties = dict()
        # allow for zProperty to be a map of zproperties that need to
        # be saved in case there is more than one
        if not isinstance(zProperty, dict):
            properties[zProperty] = value
        else:
            properties = zProperty
        for key, value in properties.iteritems():    
        # get old value for auditing
            oldProperty = facade.getZenProperty(uid, key)
            oldValue = oldProperty['value'] if 'value' in oldProperty else ''

            # change it
            facade.setZenProperty(uid, key, value)

            data = facade.getZenProperty(uid, key)
            value = str(value) if not value else value  # show 'False', '0', etc.  
            oldValue = str(oldValue) if not oldValue else oldValue  # must match
            obj = facade._getObject(uid)

            maskFields = 'value' if obj.zenPropIsPassword(zProperty) else None
            audit('UI.zProperty.Edit', zProperty, maskFields_=maskFields,
                  data_={obj.meta_type: uid, 'value': value},
                  oldData_={'value': oldValue})          
        
        return DirectResponse(data=Zuul.marshal(data))  
        
    @serviceConnectionError
    @contextRequire(ZEN_ZPROPERTIES_EDIT, 'uid')
    def deleteZenProperty(self, uid, zProperty):
        """
        Removes the local instance of the each property in properties. Note
        that the property will only be deleted if a hasProperty is true
        * also used on custom properties or cProperties
        @type  uid: String
        @param uid: unique identifier of an object
        @type  properties: String
        @param properties: zenproperty identifier
        """
        facade = self._getFacade()
        data = facade.deleteZenProperty(uid, zProperty)
        obj = facade._getObject(uid)
        audit('UI.zProperty.Delete', zProperty, data_={obj.meta_type:uid})
        return DirectResponse(data=Zuul.marshal(data))        
       
