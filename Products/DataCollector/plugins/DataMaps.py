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
#   Copyright (c) 2003 Zentinel Systems, Inc. All rights reserved.

class RelationshipMap(list):
    relname = ""
    compname = ""

    def __init__(self, relname="", compname="", modname="", objmaps=[]):
        self.relname = relname
        self.compname = compname
        self.extend([ ObjectMap(dm, modname=modname) for dm in objmaps ])



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


    def __init__(self, data={}, compname="", modname="", classname=""):
        self.updateFromDict(data)
        if compname: self.compname = compname
        if modname: self.modname = modname
        if classname: self.classname = classname


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
