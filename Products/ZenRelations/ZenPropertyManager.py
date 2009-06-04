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

import re

from OFS.PropertyManager import PropertyManager
from zExceptions import BadRequest
from Globals import DTMLFile
from Globals import InitializeClass
from Acquisition import aq_base, aq_chain
from ZPublisher.Converters import type_converters
from Products.ZenModel.ZenossSecurity import *
from AccessControl import ClassSecurityInfo
from Exceptions import zenmarker
iszprop = re.compile("^z[A-Z]").search

from Products.ZenUtils.Utils import unused

class ZenPropertyManager(PropertyManager):
    """
    ZenPropertyManager adds keyedselection type to PropertyManager.
    A keyedselection displayes a different name in the popup then
    the actual value the popup will have.

    It also has management for zenProperties which are properties that can be
    inherited long the acquision chain.  All properties are for a branch are
    defined on a "root node" specified by the function which must be returned
    by the function getZenRootNode that should be over ridden in a sub class.
    Prperties can then be added further "down" the aq_chain by calling 
    setZenProperty on any contained node.

    ZenProperties all have the same prefix which is defined by iszprop
    this can be overridden in a subclass.
    """
    __pychecker__='no-override'
    
    security = ClassSecurityInfo()
    
    manage_propertiesForm=DTMLFile('dtml/properties', globals(),
                                   property_extensible_schema__=1)
                                   
    def _setPropValue(self, id, value):
        """override from PerpertyManager to handle checks and ip creation"""
        self._wrapperCheck(value)
        if self.getPropertyType(id) == 'keyedselection':
            value = int(value)
        if not getattr(self,'_v_propdict',False):
            self._v_propdict = self.propdict()
        if self._v_propdict.has_key('setter'):
            settername = self._v_propdict['setter']
            setter = getattr(aq_base(self), settername, None)
            if not setter:
                raise ValueError("setter %s for property %s doesn't exist"
                                    % (settername, id))
            if not callable(setter):
                raise TypeError("setter %s for property %s not callable"
                                    % (settername, id))
            setter(value)
        else:
            setattr(self,id,value)


    def _setProperty(self, id, value, type='string', label=None, 
                    visible=True, setter=None):
        """for selection and multiple selection properties
        the value argument indicates the select variable
        of the property
        """
        self._wrapperCheck(value)
        if not self.valid_property_id(id):
            raise BadRequest, 'Id %s is invalid or duplicate' % id

        def setprops(**pschema):
            self._properties=self._properties+(pschema,)
            if setter: pschema['setter'] = setter
            if label: pschema['label'] = label 
            
        if type in ('selection', 'multiple selection'):
            if not hasattr(self, value):
                raise BadRequest, 'No select variable %s' % value
            setprops(id=id,type=type, visible=visible,
                     select_variable=value)    
            if type=='selection':
                self._setPropValue(id, '')
            else:
                self._setPropValue(id, [])
        else:
            setprops(id=id, type=type, visible=visible)
            valueToSet = self._transform(value, type, 'transformForSet')
            self._setPropValue(id, valueToSet)
            
    def _updateProperty(self, id, value):
        """ This method sets a property on a zope object. It overrides the
        method in PropertyManager. If Zope is upgraded you will need to check
        that this method has not changed! It is overridden so that we can catch
        the ValueError returned from the field2* converters in the class
        Converters.py
        """
        from Products.ZenWidgets import messaging
        try:
            super(ZenPropertyManager, self)._updateProperty(id, value)
        except ValueError:
            proptype = self.getPropertyType(id)
            messaging.IMessageSender(self).sendToBrowser(
                'Error Saving Property %s' % id,
                ("New value '%s' is of invalid type. "
                "It should be type '%s'") % (value, proptype),
                priority=messaging.CRITICAL
                )


    _onlystars = re.compile("^\*+$").search
    security.declareProtected(ZEN_ZPROPERTIES_EDIT, 'manage_editProperties')
    def manage_editProperties(self, REQUEST):
        """
        Edit object properties via the web.
        The purpose of this method is to change all property values,
        even those not listed in REQUEST; otherwise checkboxes that
        get turned off will be ignored.  Use manage_changeProperties()
        instead for most situations.
        """
        for prop in self._propertyMap():
            name=prop['id']
            if 'w' in prop.get('mode', 'wd'):
                value=REQUEST.get(name, '')
                if self.zenPropIsPassword(name) and self._onlystars(value):
                    continue
                self._updateProperty(name, value)
        if getattr(self, "index_object", False):
            self.index_object()
        if REQUEST:
            message="Saved changes."
            return self.manage_propertiesForm(self,REQUEST,
                                              manage_tabs_message=message)


    def getZenRootNode(self):
        """sub class must implement to use zenProperties."""
        raise NotImplementedError

    security.declareProtected(ZEN_ZPROPERTIES_VIEW, 'zenPropertyIds')
    def zenPropertyIds(self, all=True, pfilt=iszprop):
        """
        Return list of device tree property names. 
        If all use list from property root node.
        """
        if all: 
            rootnode = self.getZenRootNode()
        else: 
            if self.id == self.dmdRootName: return []
            rootnode = aq_base(self)
        props = []
        for prop in rootnode.propertyIds():
            if not pfilt(prop): continue
            props.append(prop)
        props.sort()
        return props

    security.declareProtected(ZEN_ZPROPERTIES_VIEW, 'zenPropertyItems')
    def zenPropertyItems(self):
        """Return list of (id, value) tuples of zenProperties.
        """
        return map(lambda x: (x, getattr(self, x)), self.zenPropertyIds())

    security.declareProtected(ZEN_ZPROPERTIES_VIEW, 'zenPropertyMap')
    def zenPropertyMap(self, pfilt=iszprop):
        """Return property mapping of device tree properties."""
        rootnode = self.getZenRootNode()
        pmap = []
        for pdict in rootnode.propertyMap():
            if pfilt(pdict['id']): pmap.append(pdict)
        pmap.sort(lambda x, y: cmp(x['id'], y['id']))
        return pmap

    security.declareProtected(ZEN_ZPROPERTIES_VIEW, 'zenPropertyString')
    def zenPropertyString(self, id):
        """Return the value of a device tree property as a string"""
        value = getattr(self, id, "")
        rootnode = self.getZenRootNode()
        type = rootnode.getPropertyType(id)
        if type == "lines": 
            value = "\n".join(map(str, value))
        elif self.zenPropIsPassword(id):
            value = "*"*len(value)
        return value

    security.declareProtected(ZEN_ZPROPERTIES_VIEW, 'zenPropIsPassword')
    def zenPropIsPassword(self, id):
        """Is this field a password field.
        """
        return id.endswith("assword")

    security.declareProtected(ZEN_ZPROPERTIES_VIEW, 'zenPropertyPath')
    def zenPropertyPath(self, id):
        """Return the primaryId of where a device tree property is found."""
        for obj in aq_chain(self):
            if getattr(aq_base(obj), id, zenmarker) != zenmarker:
                return obj.getPrimaryId(self.getZenRootNode().getId())

    security.declareProtected(ZEN_ZPROPERTIES_VIEW, 'zenPropertyType')
    def zenPropertyType(self, id):
        """Return the type of this property."""
        ptype = self.getZenRootNode().getPropertyType(id)
        if not ptype: ptype = "string"
        return ptype

    security.declareProtected(ZEN_ZPROPERTIES_EDIT, 'setZenProperty')
    def setZenProperty(self, propname, propvalue, REQUEST=None):
        """
        Add or set the propvalue of the property propname on this node of 
        the device Class tree.
        """
        rootnode = self.getZenRootNode()
        ptype = rootnode.getPropertyType(propname)
        if ptype == 'lines': 
            dedupedList = [] 
            for x in propvalue: 
                if x not in dedupedList: 
                    dedupedList.append(x) 
            propvalue = dedupedList
        if getattr(aq_base(self), propname, zenmarker) != zenmarker:
            self._updateProperty(propname, propvalue)
        else:
            if ptype in ("selection", 'multiple selection'): ptype="string"
            if type_converters.has_key(ptype):
                propvalue=type_converters[ptype](propvalue)
            if getattr(self, propname, None) != propvalue:
                self._setProperty(propname, propvalue, type=ptype)
        if REQUEST: return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_ZPROPERTIES_EDIT, 'saveZenProperties')
    def saveZenProperties(self, pfilt=iszprop, REQUEST=None):
        """Save all ZenProperties found in the REQUEST.form object.
        """
        for name, value in REQUEST.form.items():
            if pfilt(name):
                if self.zenPropIsPassword(name) and self._onlystars(value):
                    continue
                if name == 'zCollectorPlugins':
                    if tuple(getattr(self, name, ())) != tuple(value):
                        self.setZenProperty(name, value)
                else:
                    self.setZenProperty(name, value)

        return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_ZPROPERTIES_EDIT, 'deleteZenProperty')
    def deleteZenProperty(self, propname=None, REQUEST=None):
        """
        Delete device tree properties from the this DeviceClass object.
        """
        if propname:
            self._delProperty(propname)
        if REQUEST: return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_ZPROPERTIES_VIEW, 'zenPropertyOptions')
    def zenPropertyOptions(self, propname):
        "Provide a set of default options for a ZProperty"
        unused(propname)
        return []
    
    security.declareProtected(ZEN_ZPROPERTIES_VIEW, 'isLocal')
    def isLocal(self, propname):
        """Check to see if a name is local to our current context.
        """
        v = getattr(aq_base(self), propname, zenmarker)
        return v != zenmarker
    
    security.declareProtected(ZEN_ZPROPERTIES_VIEW, 'getOverriddenObjects')
    def getOverriddenObjects(self, propname, showDevices=False):
        """ Get the objects that override a property somewhere below in the tree
        """
        if showDevices:
            objects = []
            for inst in self.getSubInstances('devices'):
                if inst.isLocal(propname) and inst not in objects:
                    objects.append(inst) 
            for suborg in self.children():
                if suborg.isLocal(propname):
                    objects.append(suborg)
                for inst in suborg.getOverriddenObjects(propname, showDevices):
                    if inst not in objects:
                        objects.append(inst)
            return objects
        
        return [ org for org in self.getSubOrganizers() 
            if org.isLocal(propname) ]
            
    def _transform(self, value, type, method):
        """
        Lookup the transformer for the type and transform the value. The
        method parameter can be 'transformForGet' or 'transformForSet' and
        determines the transformer method that is called.
        
        The transformer lookup is performed against a dictionary that maps a
        property type to an object that has transformForGet and
        transformForSet methods. Typically the transformers dictionary is
        acquired from dmd.propertyTransformers. If self has a 
        propertyTransformers attribute (either through acquistion or dynamic
        definition), then it is used, otherwise an empty dictionary is used
        and the value is returned untouched.
        """
        transformers = getattr(self, 'propertyTransformers', {})
        if type in transformers:
            returnValue = getattr(transformers[type], method)(value)
        else:
            returnValue = value
        return returnValue
        
    def getProperty(self, id, d=None):
        """
        Get property value and apply transformer.  Overrides method in Zope's
        PropertyManager class.
        """
        return self._transform(PropertyManager.getProperty(self, id, d), 
                               self.getPropertyType(id),
                               'transformForGet')
        
InitializeClass(ZenPropertyManager)
