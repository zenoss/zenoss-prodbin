#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""ConfonPropManager

add keyedselect to property manager

$Id: ZenPropertyManager.py,v 1.4 2002/12/08 18:27:53 edahl Exp $"""

__version__ = "$Revision: 1.4 $"[11:-2]

from OFS.PropertyManager import PropertyManager
from Globals import DTMLFile
from Globals import InitializeClass
from Acquisition import aq_base, aq_chain
from ZPublisher.Converters import type_converters

from Exceptions import zenmarker


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

    ZenProperties all have the same prefix which is defined by zenPropertyPrefix
    this can be overridden in a subclass.
    """

    zenPropertyPrefix = "zen"

    manage_propertiesForm=DTMLFile('dtml/properties', globals(),
                                   property_extensible_schema__=1)
    
    def _setPropValue(self, id, value):
        """override from PerpertyManager to handle checks and ip creation"""
        self._wrapperCheck(value)
        if self.getPropertyType(id) == 'keyedselection':
            value = int(value)
        setattr(self,id,value)


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


    def zenPropertyIds(self, all=True):
        """
        Return list of device tree property names. 
        If all use list from property root node.
        """
        if all: 
            rootnode = self.getZenRootNode()
        else: 
            if self.id == "Devices": return []
            rootnode = aq_base(self)
        props = []
        for prop in rootnode.propertyIds():
            if not prop.startswith(self.zenPropertyPrefix): continue
            props.append(prop)
        props.sort()
        return props


    def zenPropertyMap(self):
        """Return property mapping of device tree properties."""
        rootnode = self.getZenRootNode()
        pnames = self.zenPropertyIds()
        pmap = []
        for pdict in rootnode.propertyMap():
            if pdict['id'] in pnames:
                pmap.append(pdict)
        pmap.sort(lambda x, y: cmp(x['id'], y['id']))
        return pmap
            

    def zenPropertyString(self, id):
        """Return the value of a device tree property as a string"""
        value = getattr(self, id, "")
        rootnode = self.getZenRootNode()
        type = rootnode.getPropertyType(id)
        if type == "lines": 
            value = ", ".join(value)
        return value


    def zenPropertyPath(self, id):
        """Return the primaryId of where a device tree property is found."""
        for obj in aq_chain(self):
            if getattr(aq_base(obj), id, zenmarker) != zenmarker:
                return obj.getPrimaryId(self.getZenRootNode().getId())


    def zenPropertyType(self, id):
        """Return the type of this property."""
        return self.getZenRootNode().getPropertyType(id)

    
    def setZenProperty(self, propname, propvalue, REQUEST=None):
        """
        Add or set the propvalue of the property propname on this node of 
        the device Class tree.
        """
        rootnode = self.getZenRootNode()
        ptype = rootnode.getPropertyType(propname)
        if ptype == "lines": 
            propvalue = propvalue.split(",")
            propvalue = map(lambda x: x.strip(), propvalue)
        if getattr(aq_base(self), propname, zenmarker) != zenmarker:
            self._updateProperty(propname, propvalue)
        else:
            if type_converters.has_key(ptype):
                propvalue=type_converters[ptype](propvalue)
            self._setProperty(propname, propvalue, type=ptype)
        if REQUEST: return self.callZenScreen(REQUEST)

    
    def deleteZenProperty(self, propname, REQUEST=None):
        """
        Delete device tree properties from the this DeviceClass object.
        """
        self._delProperty(propname)
        if REQUEST: return self.callZenScreen(REQUEST)
         
    
InitializeClass(ZenPropertyManager)
