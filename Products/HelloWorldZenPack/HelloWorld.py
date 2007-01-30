#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

from OFS.PropertyManager import PropertyManager
from Products.ZenRelations.RelationshipManager import RelationshipManager as RM
from Products.ZenRelations.RelSchema import *
from Products.ZenRelations.Exceptions import *

class HelloWorldClass(RM):
    zenRelationsBaseModule = "Products.HelloWorldZenPack"

class DataRoot(HelloWorldClass):

    def manage_afterAdd(self, item, container):
        self.zPrimaryBasePath = container.getPhysicalPath()
        HelloWorldClass.manage_afterAdd(self, item, container)

class Device(HelloWorldClass, PropertyManager):
    _properties = (
        {'id':'pingStatus', 'type':'int', 'mode':'w', 'setter':'setPingStatus'},
        )
    _relations = (
        ("location", ToOne(ToMany, "HelloWorld.Location", "devices")),
        ("groups", ToMany(ToMany, "HelloWorld.Group", "devices")),
        )
    pingStatus = 0 
    communities = ()

class Group(HelloWorldClass):
    _relations = (
        ("devices", ToMany(ToMany, "HelloWorld.Device", "groups")),
        )
class Location(HelloWorldClass):
    _relations = (
        ("devices", ToMany(ToOne, "HelloWorld.Device", "location")),
        )

class Admin(HelloWorldClass):
    _relations = (
        ("device", ToOne(ToOne, "HelloWorld.Device", "admin")),
        )

class Organizer(HelloWorldClass):
    _relations = (
    ("parent", ToOne(ToManyCont,"HelloWorld.Organizer","children")),
    ("children", ToManyCont(ToOne,"HelloWorld.Organizer","parent")),
    )
    def buildOrgProps(self):
        self._setProperty("zFloat", -1.0, type="float")
        self._setProperty("zInt", -1, type="int")
        self._setProperty("zString", "", type="string")
        self._setProperty("zBool", True, type="boolean")
        self._setProperty("zLines", [], type="lines")

    def getZenRootNode(self):
        return self.unrestrictedTraverse("/zport/dmd/Orgs")


def create(context, klass, id):
    """create an instance and attach it to the context passed"""
    inst = klass(id)
    context._setObject(id, inst)
    inst = context._getOb(id)
    return inst

def initHelloWorldSkins(self):
    """setup the skins that come with HelloWorldZenPack"""
    layers = ('helloWorld',)
    try:
        import string 
        from Products.CMFCore.utils import getToolByName
        from Products.CMFCore.DirectoryView import addDirectoryViews
        skinstool = getToolByName(self, 'portal_skins') 
        for layer in layers:
            if layer not in skinstool.objectIds():
                addDirectoryViews(skinstool, 'skins', globals())
        skins = skinstool.getSkinSelections()
        for skin in skins:
            path = skinstool.getSkinPath(skin)
            path = map(string.strip, string.split(path,','))
            for layer in layers:
                if layer not in path:
                    try:
                        path.insert(path.index('custom')+1, layer)
                    except ValueError:
                        path.append(layer)
            path = ','.join(path)
            skinstool.addSkinSelection(skin, path)
    except ImportError, e:
        if "Products.CMFCore.utils" in e.args: pass
        else: raise
    except AttributeError, e:
        if "portal_skin" in e.args: pass
        else: raise
        
build = create

