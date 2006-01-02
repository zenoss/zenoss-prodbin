#################################################################
#
#   Copyright (c) 2003 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

class RelationshipMap(list):
    relname = ""
    compname = ""


class ObjectMap(object):
    """
    ObjectMap defines a mapping of some data to a ZenModel object.  To be valid
    it must specify modname the full path to the module where the class to 
    be created is defined.  If the class name is the same as the module
    classname doesn't need to be defined.  
    """
    compname = ""
    modname = ""
    classname = ""
    _blockattrs = ('compname', 'modname', 'classname' )
    _attrs = []


    def __init__(self, data={}):
        self.updateFromDict(data)


    def __setattr__(self, name, value):
        if name not in self._attrs and not name.startswith("_"): 
            self._attrs.append(name)
        self.__dict__[name] = value


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
