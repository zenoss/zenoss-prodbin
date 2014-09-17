##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import re
from zope.interface import implements
from Products.Zuul.facades import ZuulFacade
from Products.Zuul.interfaces import IPropertiesFacade
from DateTime import DateTime
iscustprop = re.compile("c[A-Z]").match


class PropertiesFacade(ZuulFacade):
    implements(IPropertiesFacade)

    def getZenProperties(self, uid, exclusionList=()):
        """
        Returns information about and the value of every zen property.  

        @type  uid: string
        @param uid: unique identifier of an object
        @type  exclusionList: Collection
        @param exclusionList: List of zproperty ids that we do not wish to retrieve
        """
        obj = self._getObject(uid)
        return obj.exportZProperties(exclusionList)

    def deleteZenProperty(self, uid, zProperty):
        """
        Removes the local instance of the each property in properties. Note
        that the property will only be deleted if a hasProperty is true
        @type  uid: String
        @param uid: unique identifier of an object
        @type  properties: Array
        @param properties: list of zenproperty identifiers that we wish to delete
        """
        obj = self._getObject(uid)
        if obj.hasProperty(zProperty):
            prop = self.getZenProperty(uid, zProperty)
            if not iscustprop(zProperty):
                if prop['path'] == '/':
                    raise Exception('Unable to delete root definition of a property')
                    
            obj.deleteZenProperty(zProperty) 
            
    def _checkType(self, obj, prop, type, value):
        """
        @param obj: the object returned in the caller from getObject(uid)
        @param prop: the id, zProperty, or cProperty
        @param type: the type of property value
        @param value: the value itself
        """        
        # make sure it is the correct type
        ztype = obj.getPropertyType(prop)
        if ztype == 'int':
            value = int(value)
        if ztype == 'float':
            value = float(value)
        if ztype == 'string':
            value = str(value)
        if ztype == 'date':
            value = value.replace('%20', ' ') # Ugh. Manually decode spaces
            value = DateTime(value)
        if ztype == "lines" and isinstance(value, basestring):
            value = value.split("\n")
        return value    
 
    def addCustomProperty(self, id, value, label, uid, type):
        """
        adds a custom property from the UI
        """
        obj = self._getObject(uid)
            
        value = self._checkType(obj, id, type, value)  
            
        id = id.strip()    
        if not iscustprop(id):
            raise Exception("Invalid Custom Property. Must start with lower case c")
        elif obj.hasProperty(id):
            raise Exception("Custom Property already exists.")
        else:
            obj._setProperty(id, value, type, label)
            

    def setZenProperty(self, uid, zProperty, value):
        """
        Sets the value of the zProperty for this user.
        The value will be forced into the type, throwing
        an exception if it fails
        @type  uid: String
        @param uid: unique identifier of an object
        @type  zProperty: String
        @param zProperty: identifier of the property
        @type  value: Anything
        @param value: What you want the new value of the property to be
        """
        obj = self._getObject(uid)
        # make sure it is the correct type
        value = self._checkType(obj, zProperty, type, value)
        # do not save * as passwords
        if obj.zenPropIsPassword(zProperty) and value == obj.zenPropertyString(zProperty):
            return
               
        return obj.setZenProperty(zProperty, value)                       
    
    def getCustomProperties(self, uid, exclusionList=()):
        """
        Returns information about and the value of every zen property.

        @type  uid: string
        @param uid: unique identifier of an object
        @type  exclusionList: Collection
        @param exclusionList: List of cproperty ids that we do not wish to retrieve
        """
        obj = self._getObject(uid)
        return self.exportCustomProperties(obj, exclusionList)
    
    def exportCustomProperties(self, obj, exclusionList=()):
        """
        TODO: This really belongs in ZenRelations/ZenRelationManager.py

        @param exclusionList: list of cproperties we do not want to export
        @type exclusionList: collection

        For this manager will return the following about each cProperty
        Will return the following about each Zen Property
        - id - identifier
        - islocal - if this object has a local definition
        - value - value for this object
        - valueAsString - string representation of the property
        - type - int string lines etc
        - path - where it is defined
        - options - acceptable values of this zProperty
        """
        props = []
        for entry in obj.custPropertyMap():
            cId = entry["id"]
            if cId in exclusionList:
                continue
            prop = dict(
                    id=cId,
                    islocal=obj.hasProperty(cId),
                    type=obj.getPropertyType(cId),
                    path=obj.zenPropertyPath(cId),
                    options=obj.zenPropertyOptions(cId),
                    label=entry.get("label"),
                    value=None,
                    valueAsString=obj.zenPropertyString(cId)
                    )
            if not obj.zenPropIsPassword(cId):
                prop['value'] = obj.getZ(cId)
            else:
                prop['value'] = obj.zenPropertyString(cId)
            props.append(prop)
        return props  

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
        obj = self._getObject(uid)
        prop = dict(
            path = obj.zenPropertyPath(zProperty),
            options = obj.zenPropertyOptions(zProperty),
            type=obj.getPropertyType(zProperty),
            )

        if not obj.zenPropIsPassword(zProperty):
            prop['value'] = obj.getZ(zProperty)
            prop['valueAsString'] = obj.zenPropertyString(zProperty)
        return prop         
