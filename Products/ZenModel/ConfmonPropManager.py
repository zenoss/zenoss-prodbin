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

__doc__="""ConfonPropManager

add keyedselect to property manager

$Id: ConfmonPropManager.py,v 1.4 2002/12/08 18:27:53 edahl Exp $"""

__version__ = "$Revision: 1.4 $"[11:-2]

from OFS.PropertyManager import PropertyManager
from Globals import DTMLFile
from Globals import InitializeClass
from Acquisition import aq_base

class ConfmonPropManager(PropertyManager):

    manage_propertiesForm=DTMLFile('dtml/properties', globals(),
                                   property_extensible_schema__=1)
    
    def _setPropValue(self, id, value):
        """override from PerpertyManager to handle checks and ip creation"""
        self._wrapperCheck(value)
        if self.getPropertyType(id) == 'keyedselection':
            value = int(value)
        setattr(self,id,value)


    def manage_editProperties(self, REQUEST):
        """Edit object properties via the web.
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
        self.index_object()
        if REQUEST:
            message="Saved changes."
            return self.manage_propertiesForm(self,REQUEST,
                                              manage_tabs_message=message)


InitializeClass(ConfmonPropManager)
