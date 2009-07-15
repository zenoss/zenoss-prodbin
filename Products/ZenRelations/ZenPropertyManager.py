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

# Z_PROPERTIES is a list of (id, type, value) pairs that define all the 
# zProperties.  The values are set on dmd.Devices in the 
# buildDeviceTreeProperties of DeviceClass
Z_PROPERTIES = [
    
    # zPythonClass maps device class to python classs (separate from device
    # class name)
    ('zPythonClass', 'string', ''),
    
    # zProdStateThreshold is the production state threshold at which to start
    # monitoring boxes
    ('zProdStateThreshold', 'int', 300),
    
    # zIfDescription determines whether or not the ifdescripion field is
    # displayed
    ('zIfDescription', 'boolean', False),
    
    # Snmp collection properties
    ('zSnmpCommunities', 'lines', ['public', 'private']),
    ('zSnmpCommunity', 'string', 'public'),
    ('zSnmpPort', 'int', 161),
    ('zSnmpVer', 'string', 'v1'),
    ('zSnmpTries', 'int', 2),
    ('zSnmpTimeout', 'float', 2.5),
    ('zSnmpSecurityName', 'string', ''),
    ('zSnmpAuthPassword', 'password', ''),
    ('zSnmpPrivPassword', 'password', ''),
    ('zSnmpAuthType', 'string', ''),
    ('zSnmpPrivType', 'string', ''),
    ('zRouteMapCollectOnlyLocal', 'boolean', False),
    ('zRouteMapCollectOnlyIndirect', 'boolean', False),
    ('zRouteMapMaxRoutes', 'int', 500),
    ('zInterfaceMapIgnoreTypes', 'string', ''),
    ('zInterfaceMapIgnoreNames', 'string', ''),
    ('zFileSystemMapIgnoreTypes', 'lines', []),
    ('zFileSystemMapIgnoreNames', 'string', ''),
    ('zFileSystemSizeOffset', 'float', 1.0),
    ('zHardDiskMapMatch', 'string', ''),
    ('zSysedgeDiskMapIgnoreNames', 'string', ''),
    ('zIpServiceMapMaxPort', 'int', 1024),
    ('zDeviceTemplates', 'lines', ['Device']),
    ('zLocalIpAddresses', 'string', '^127|^0\\.0|^169\\.254|^224'),
    ('zLocalInterfaceNames', 'string', '^lo|^vmnet'),
    
    # Ping monitor properties
    ('zPingInterfaceName', 'string', ''),
    ('zPingInterfaceDescription', 'string', ''),
    
    # Status monitor properties
    ('zSnmpMonitorIgnore', 'boolean', False),
    ('zPingMonitorIgnore', 'boolean', False),
    ('zWmiMonitorIgnore', 'boolean', True),
    ('zStatusConnectTimeout', 'float', 15.0),
    
    # DataCollector properties
    ('zCollectorPlugins', 'lines', []),
    ('zCollectorClientTimeout', 'int', 180),
    ('zCollectorDecoding', 'string', 'latin-1'),
    ('zCommandUsername', 'string', ''),
    ('zCommandPassword', 'password', ''),
    ('zCommandProtocol', 'string', 'ssh'),
    ('zCommandPort', 'int', 22),
    ('zCommandLoginTries', 'int', 1),
    ('zCommandLoginTimeout', 'float', 10.0),
    ('zCommandCommandTimeout', 'float', 10.0),
    ('zCommandSearchPath', 'lines', []),
    ('zCommandExistanceTest', 'string', 'test -f %s'),
    ('zCommandPath', 'string', '/usr/local/zenoss/libexec'),
    ('zTelnetLoginRegex', 'string', 'ogin:.$'),
    ('zTelnetPasswordRegex', 'string', 'assword:'),
    ('zTelnetSuccessRegexList', 'lines', ['\\$.$', '\\#.$']),
    ('zTelnetEnable', 'boolean', False),
    ('zTelnetEnableRegex', 'string', 'assword:'),
    ('zTelnetTermLength', 'boolean', True),
    ('zTelnetPromptTimeout', 'float', 10.0),
    ('zKeyPath', 'string', '~/.ssh/id_dsa'),
    ('zMaxOIDPerRequest', 'int', 40),
    
    # Extra stuff for users
    ('zLinks', 'string', ''),
    
    # Windows WMI collector properties
    ('zWinUser', 'string', ''),
    ('zWinPassword', 'password', ''),
    ('zWinEventlogMinSeverity', 'int', 2),
    ('zWinEventlog', 'boolean', False),
    
    # zIcon is the icon path
    ('zIcon', 'string', '/zport/dmd/img/icons/noicon.png'),
    ]
    
class PropertyDescriptor(object):
    """
    Transforms the property value based on its type.
    
    Follows the Descriptor protocol defined at
    http://docs.python.org/reference/datamodel.html#descriptors
    """
    
    def __init__(self, id, type):
        self.id = id
        self.type = type
        
    def __get__(self, instance, owner):
        """
        Returns self for class attribute access.  Returns the transformed
        value for instance attribute access.  Raises an AttributeError is
        things go poorly.
        """
        try:
            return self._get(instance)
        except AttributeError:
            raise
        except Exception, e:
            raise AttributeError(e)
            
    def __set__(self, instance, value):
        """
        Transforms the value and sets it.
        """
        self._migrate(instance)
        self._set(instance, value)
        
    def __delete__(self, instance):
        """
        Delete the property.
        """
        self._migrate(instance)
        del instance._propertyValues[self.id]
        
    def _get(self, instance):
        """
        Returns self for class attribute access.  Returns the transformed
        value for instance attribute access.
        """
        if instance is None:
            retval = self
        else:
            self._migrate(instance)
            value = instance._propertyValues[self.id]
            retval = instance._transform(value, self.type, 'transformForGet')
        return retval
        
    def _migrate(self, instance):
        """
        If the id is in __dict__ then move the value to the _propertyValues
        dictionary.
        """
        if not hasattr(instance, '_propertyValues'):
            instance._propertyValues = {}
        if self.id in vars(instance):
            self._set(instance, vars(instance)[self.id])
            del instance.__dict__[self.id]
            
    def _set(self, instance, value):
        """
        Transform and set the value in the _propertyValues dictionary.
        """
        valueToSet = instance._transform(value, self.type, 'transformForSet')
        instance._propertyValues[self.id] = valueToSet
        
class ZenPropertyManager(object, PropertyManager):
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
    
    ZenPropertyManager overrides getProperty and getPropertyType from 
    PropertyManager to support acquisition. If you want to query an object
    about a property, but do not want it to search the acquistion chain then
    use the super classes method or aq_base.  Example:
        
        # acquires property from dmd.Devices
        dmd.Devices.Server.getProperty('zCollectorPlugins')
        
        # does not acquire property from dmd.Devices
        PropertyManager.getProperty(dmd.Devices.Server, 'zCollectorPlugins')
        
        # also does not acquire property from dmd.Devices
        aq_base(dmd.Devices.Server).getProperty('zSnmpCommunity')
        
    The properties are stored as attributes which is convenient, but can be 
    confusing.  Attribute access always uses acquistion.  Setting an
    attribute, will not add it to the list of properties, so subsquent calls
    to hasProperty or getProperty won't return it.
    
    Property Transformers are stored at dmd.propertyTransformers and transform
    the property based on type during calls to the _setProperty, 
    _updateProperty, and getProperty methods. Adding a property using 
    _setProperty applies the appropriate transformer and adds its value as an
    attribute, but when you access it as an attribute the property transformer
    is not applied.  Instead of attribute access, you should always use the
    getProperty method.
    """
    __pychecker__='no-override'
    
    security = ClassSecurityInfo()
    
    manage_propertiesForm=DTMLFile('dtml/properties', globals(),
                                   property_extensible_schema__=1)
                                   
    def _setPropValue(self, id, value):
        """override from PerpertyManager to handle checks and ip creation"""
        self._wrapperCheck(value)
        
        # copy acquired propertyTransformers to this instance, because the
        # PropertyDescriptor methods are called with instance parameters that
        # no longer have their acquisition wrapper
        if hasattr(self, 'dmd') and hasattr(self.dmd, 'propertyTransformers'):
            self.propertyTransformers = self.dmd.propertyTransformers
            
        propType = self.getPropertyType(id)
        if  propType == 'keyedselection':
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
            setattr(self, id, value)


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
            self._setPropValue(id, value)
            
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
        def displayLines(lines):
            return '\n'.join([str(line) for line in lines])
        def displayPassword(password):
            return '*' * len(password)
        def displayOthers(other):
            return other
        displayFunctions = {'lines': displayLines,
                            'password': displayPassword}
        display = displayFunctions.get(self.getPropertyType(id), 
                                       displayOthers)
        return display(self.getProperty(id, ''))
        
    security.declareProtected(ZEN_ZPROPERTIES_VIEW, 'zenPropIsPassword')
    def zenPropIsPassword(self, id):
        """Is this field a password field.
        """
        return self.getPropertyType(id) == 'password'

    security.declareProtected(ZEN_ZPROPERTIES_VIEW, 'zenPropertyPath')
    def zenPropertyPath(self, id):
        """Return the primaryId of where a device tree property is found."""
        ob = self._findParentWithProperty(id)
        if ob is None:
            path = None
        else:
            path = ob.getPrimaryId(self.getZenRootNode().getId())
        return path
                
    security.declareProtected(ZEN_ZPROPERTIES_EDIT, 'setZenProperty')
    def setZenProperty(self, propname, propvalue, REQUEST=None):
        """
        Add or set the propvalue of the property propname on this node of 
        the device Class tree.
        """
        ptype = self.getPropertyType(propname)
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
        property type to a callable factory that creates objects that have 
        transformForGet and transformForSet methods. Typically the
        transformers dictionary is acquired from dmd.propertyTransformers. If
        self has a propertyTransformers attribute (either through acquistion
        or dynamic definition), then it is used, otherwise an empty dictionary
        is used and the value is returned untouched.
        """
        factories = getattr(self, 'propertyTransformers', {})
        if type in factories:
            transformer = factories[type]()
            returnValue = getattr(transformer, method)(value)
        else:
            returnValue = value
        return returnValue

    def _findParentWithProperty(self, id):
        """
        Returns self or the first acquisition parent that has a property with
        the id.  Returns None if no parent had the id.
        """
        for ob in aq_chain(self):
            if isinstance(ob, ZenPropertyManager) and ob.hasProperty(id):
                parentWithProperty = ob
                break
        else:
            parentWithProperty = None
        return parentWithProperty
        
    def hasProperty(self, id, useAcquisition=False):
        """
        Override method in PropertyManager to support acquisition.
        """
        if useAcquisition:
            hasProp = self._findParentWithProperty(id) is not None
        else:
            hasProp = PropertyManager.hasProperty(self, id)
        return hasProp
        
    def getProperty(self, id, d=None):
        """
        Get property value and apply transformer.  Overrides method in Zope's
        PropertyManager class.  Acquire values from aquisiton parents if
        needed.
        """
        ob = self._findParentWithProperty(id)
        if ob is None:
            value = d
        else:
            value = PropertyManager.getProperty(ob, id, d)
        return value
        
    security.declareProtected(ZEN_ZPROPERTIES_VIEW, 'getPropertyType')
    def getPropertyType(self, id):
        """
        Overrides methods from PropertyManager to support acquistion.
        """
        ob = self._findParentWithProperty(id)
        if ob is None:
            type = None
        else:
            type = PropertyManager.getPropertyType(ob, id)
        return type
        
    security.declareProtected(ZEN_ZPROPERTIES_VIEW, 'getZ')
    def getZ(self, id):
        """
        Return the value of a zProperty on this object.  This method is used to
        lookup zProperties for a user with a role that doesn't have direct
        access to an attribute further up the acquisition path.  If the
        requested property is a password, then None is returned.

        @param id: id of zProperty
        @type id: string
        @return: Value of zProperty
        @permission: ZEN_ZPROPERTIES_VIEW

        >>> dmd.Devices.getZ('zSnmpPort')
        161
        >>> dmd.Devices.getZ('zWinPassword')
        >>>
        """
        if self.hasProperty(id, useAcquisition=True) \
                and not self.zenPropIsPassword(id):
            returnValue = self.getProperty(id)
        else:
            returnValue = None
        return returnValue
        
for id, type, value in Z_PROPERTIES:
    setattr(ZenPropertyManager, id, PropertyDescriptor(id, type))
        
InitializeClass(ZenPropertyManager)
