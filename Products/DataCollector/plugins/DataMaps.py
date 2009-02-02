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

from pprint import pformat

from twisted.spread import pb

class PBSafe(pb.Copyable, pb.RemoteCopy): pass

class RelationshipMap(PBSafe):
    relname = ""
    compname = ""

    def __init__(self, relname="", compname="", modname="", objmaps=[]):
        self.relname = relname
        self.compname = compname
        self.maps = [ObjectMap(dm, modname=modname) for dm in objmaps ]
    
    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, pformat(self.maps))

    def __iter__(self):
        return iter(self.maps)

    def append(self, obj):
        self.maps.append(obj)

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
