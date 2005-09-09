#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

from OFS.PropertyManager import PropertyManager
from Products.ZenRelations.RelationshipManager import RelationshipManager

# Test schema classes see schema.data for relationships
class Device(RelationshipManager, PropertyManager):
    _properties = (
                    {'id':'pingStatus', 'type':'int', 
                        'mode':'w', 'setter':'setPingStatus'},
                  )

class Server(Device):pass
class IpInterface(RelationshipManager):pass
class Group(RelationshipManager):pass
class Location(RelationshipManager):pass
class Admin(RelationshipManager):pass


def create(context, klass, id):
    """create an instance and attach it to the context passed"""
    inst = klass(id)
    context._setObject(id, inst)
    inst = context._getOb(id)
    return inst


def build(context, klass, id):
    """create instance attache to context and build relationships"""
    inst = klass(id)
    context._setObject(id, inst)
    inst = context._getOb(id)
    inst.buildRelations()
    return inst
