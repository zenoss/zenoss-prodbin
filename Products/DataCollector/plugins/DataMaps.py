##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007-2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

import logging
log = logging.getLogger("zen.plugins.DataMap")

from pprint import pformat
from pprint import pprint
from twisted.spread import pb

class PBSafe(pb.Copyable, pb.RemoteCopy): pass

class RelationshipMap(PBSafe):
    parentId = ""
    relname = ""
    compname = ""

    def __init__(self, parentId="", relname="", compname="", modname="", objmaps=[]):
        self.parentId = parentId
        self.relname = relname
        self.compname = compname
        if modname:
            self.maps = [ObjectMap(dm, modname=modname) for dm in objmaps ]
        else:
            self.maps = [ObjectMap(dm) for dm in objmaps ]

    def __repr__(self):
        display = self.__dict__.copy()
        del display['maps']
        display['objmaps'] = self.maps
        return '<%s %s>' % (self.__class__.__name__, pformat(display))

    def __iter__(self):
        return iter(self.maps)

    def append(self, obj):
        self.maps.append(obj)

    def extend(self, objmaps):
        self.maps.extend(objmaps)

    def asUnitTest(self):
        """
        Return the results of the relationship map as something that can
        be used directly for unit tests.
        """
        return pformat(dict((map.id, map.asUnitTest()) for map in self.maps))

pb.setUnjellyableForClass(RelationshipMap, RelationshipMap)


class ObjectMap(PBSafe):
    """
    ObjectMap defines a mapping of some data to a ZenModel object.  To be valid
    it must specify modname the full path to the module where the class to 
    be created is defined.  If the class name is the same as the module
    classname doesn't need to be defined.  
    """
    compname = ""
    modname = ""
    classname = ""
    _blockattrs = ('compname', 'modname', 'classname')
    _attrs = []

    def __init__(self, data={}, compname="", modname="", classname=""):
        self._attrs = []
        self.updateFromDict(data)
        if compname: self.compname = compname
        if modname: self.modname = modname
        if classname: self.classname = classname

    def __setattr__(self, name, value):
        if name not in self._attrs and not name.startswith("_"):
            self._attrs.append(name)
        self.__dict__[name] = value
        
    def __repr__(self):
        map = {}
        map.update(self.__dict__)
        del map["_attrs"]
        return '<%s %s>' % (self.__class__.__name__, pformat(map))

    def items(self):
        """Return the name value pairs for this ObjectMap.
        """
        return [ (n, v) for n, v in self.__dict__.items() \
                if n not in self._blockattrs and n in self._attrs ]

    def updateFromDict(self, data):
        """Update this ObjectMap from a dictionary's values.
        """
        for key, value in data.items():
            setattr(self, key, value)

    def asUnitTest(self):
        """
        Return the results of the object map as something that can
        be used directly for unit tests.
        """
        map = {}
        map.update(self.__dict__)
        del map["_attrs"]
        if not map["classname"]:
            del map["classname"]
        if not map["compname"]:
            del map["compname"]
        return map


pb.setUnjellyableForClass(ObjectMap, ObjectMap)

class MultiArgs(PBSafe):
    """
    Can be used as the value in an ObjectMap when the key is a function that 
    takes multiple arguments.
    """
    
    def __init__(self, *args):
        self.args = args
        
        
    def __repr__(self):
        return str(self.args)
    
    
pb.setUnjellyableForClass(MultiArgs, MultiArgs)
