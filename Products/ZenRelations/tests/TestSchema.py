#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

from OFS.PropertyManager import PropertyManager
from Products.ZenRelations.RelationshipManager import RelationshipManager as RM
from Products.ZenRelations.RelSchema import *
from Products.ZenRelations.Exceptions import *

class TestBaseClass(RM):
    zenRelationsBaseModule = "Products.ZenRelations.tests"

class DataRoot(TestBaseClass): 

    def manage_afterAdd(self, item, container):
        self.zPrimaryBasePath = container.getPhysicalPath()
        TestBaseClass.manage_afterAdd(self, item, container)

class Device(TestBaseClass, PropertyManager):
    _properties = (
        {'id':'pingStatus', 'type':'int', 'mode':'w', 'setter':'setPingStatus'},
        )
    _relations = (
        ("location", ToOne(ToMany, "TestSchema.Location", "devices")),
        ("groups", ToMany(ToMany, "TestSchema.Group", "devices")),
        ("interfaces", ToManyCont(ToOne, "TestSchema.IpInterface", "device")),
        )
    pingStatus = 0 


class Server(Device):
    _relations = (
        ("admin", ToOne(ToOne, "TestSchema.Admin", "server")),
        ) + Device._relations

class IpInterface(TestBaseClass):
    _relations = (
        ("device", ToOne(ToMany,"TestSchema.Device","ipinterfaces")),
        )
    beforeDelete = False
    afterAdd = False
    def manage_beforeDelete(self, item, container):
        self.beforeDelete = True
    def manage_afterAdd(self, item, container):
        if (not hasattr(self, "__primary_parent__") or 
            item.__primary_parent__ != container): 
            raise ZenRelationsError("__primary_parent__ not set in afterAdd")
        self.afterAdd = True

class Group(TestBaseClass):
    _relations = (
        ("devices", ToMany(ToMany, "TestSchema.Device", "groups")),
        )
class Location(TestBaseClass):
    _relations = (
        ("devices", ToMany(ToOne, "TestSchema.Device", "location")),
        )

class Admin(TestBaseClass):
    _relations = (
        ("server", ToOne(ToOne, "TestSchema.Server", "admin")),
        )

class Organizer(TestBaseClass):
    _relations = (
    ("parent", ToOne(ToManyCont,"TestSchema.Organizer","children")),
    ("children", ToManyCont(ToOne,"TestSchema.Organizer","parent")),
    )
    def buildOrgProps(self):
        self._setProperty("zenFloat", -1.0, type="float")
        self._setProperty("zenInt", -1, type="int")
        self._setProperty("zenString", "", type="string")
        self._setProperty("zenBool", True, type="boolean")
        self._setProperty("zenLines", [], type="lines")

    def getZenRootNode(self):
        return self.unrestrictedTraverse("/dataroot/Orgs")


def create(context, klass, id):
    """create an instance and attach it to the context passed"""
    inst = klass(id)
    context._setObject(id, inst)
    inst = context._getOb(id)
    return inst
build = create
