#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""SnmpTableMap

manages a map of a snmp table oid and its columns to a relationship
and its related object attributes

$Id: SnmpPropertyManager.py,v 1.2 2002/06/14 14:33:46 edahl Exp $"""

__version__ = "$Revision: 1.2 $"[11:-2]

from OFS.PropertyManager import PropertyManager
from Globals import DTMLFile
from Acquisition import aq_base

class SnmpPropertyManager(PropertyManager):

    manage_propertiesForm=DTMLFile('dtml/properties', globals(),
                                   property_extensible_schema__=1)
    
    def _setPropValue(self, id, value):
        """override from PerpertyManager to handle checks and ip creation"""
        self._wrapperCheck(value)
        if self.getPropertyType(id)[:3] == 'oid':
            self._oidmap[id] = value
        else:    
            setattr(self,id,value)


    def _delPropValue(self, id):
        if self.getPropertyType(id)[:3] == 'oid':
            del self._oidmap[id]
        else:        
            delattr(self,id)


    def getProperty(self, id, d=None):
        """Get the property 'id', returning the optional second 
           argument or None if no such property is found."""
        if self.hasProperty(id):
            if self.getPropertyType(id)[:3] == 'oid':
                return self._oidmap[id]
            else:    
                return getattr(self, id)
        return d


    def manage_delProperties(self, ids=None, REQUEST=None):
        """Delete one or more properties specified by 'ids'.
        override hasattr check to also look in the oidmap"""

        if ids is None:
            return MessageDialog(
                   title='No property specified',
                   message='No properties were specified!',
                   action ='./manage_propertiesForm',)
        propdict=self.propdict()
        nd=self._reserved_names
        for id in ids:
            if (not hasattr(aq_base(self), id) 
                and not self._oidmap.has_key(id)):
                raise 'BadRequest', (
                      'The property <em>%s</em> does not exist' % id)
            if (not 'd' in propdict[id].get('mode', 'wd')) or (id in nd):
                return MessageDialog(
                title  ='Cannot delete %s' % id,
                message='The property <em>%s</em> cannot be deleted.' % id,
                action ='manage_propertiesForm')
            self._delProperty(id)

        if REQUEST is not None:
            return self.manage_propertiesForm(self, REQUEST)


    def _delProperty(self, id):
        if not self.hasProperty(id):
            raise ValueError, 'The property %s does not exist' % id

        if self.getPropertyType(id)[:3] == 'oid':
            del self._oidmap[id]
        else:    
            delattr(self,id)
        self._properties=tuple(filter(lambda i, n=id: i['id'] != n,
                                      self._properties))
