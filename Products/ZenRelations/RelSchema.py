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

__doc__="""$Id: ToManyRelationship.py,v 1.48 2003/11/12 22:05:48 edahl Exp $"""

__version__ = "$Revision: 1.48 $"[11:-2]


RELMETATYPES = (
    'ToOneRelationship', 'ToManyContRelationship', 'ToManyRelationship')

class RelSchema:

    def __init__(self, remoteType, remoteClass, remoteName):
        self.remoteType = remoteType
        self.remoteClass = remoteClass
        self.remoteName = remoteName 
    
    def createRelation(self, name):
        return self._relationClass(name)

    def checkType(self, relationship):
        """Check that a relationship instance is of correct type"""
        return isinstance(relationship, self._relationClass)


class ToOne(RelSchema):
    from ToOneRelationship import ToOneRelationship
    _relationClass = ToOneRelationship    

class ToMany(RelSchema):
    from ToManyRelationship import ToManyRelationship
    _relationClass = ToManyRelationship

class ToManyCont(RelSchema):
    from ToManyContRelationship import ToManyContRelationship
    _relationClass = ToManyContRelationship
