#################################################################
#
#   Copyright (c) 2007 Zenoss, Inc. All rights reserved.
#
#################################################################
import zope.interface

from Globals import InitializeClass
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenModel import interfaces
from Products.ZenRelations.RelSchema import *

import transaction

import os

__doc__="ZenPacks base definitions"

class ZenPack(ZenModelRM):
    '''The root of all ZenPacks: has no implementation,
    but sits here to be the target of the Relation'''

    objectPaths = None
    author = ''
    organization = ''
    url = ''

    _properties = ZenModelRM._properties + (
        {'id':'objectPaths','type':'lines','mode':'w'},
        {'id':'author', 'type':'string', 'mode':'w'},
        {'id':'organization', 'type':'string', 'mode':'w'},
        {'id':'url', 'type':'string', 'mode':'w'},
    )
    
    _relations =  (
        ('root', ToOne(ToManyCont, 'DataRoot', 'packs')),
        ("packables", ToMany(ToOne, "ZenPackable", "pack")),
        )

    factory_type_information = (
        { 'immediate_view' : 'viewPackDetail',
          'actions'        :
          (
           { 'id'            : 'viewPackDetail'
             , 'name'          : 'Detail'
             , 'action'        : 'viewPackDetail'
             , 'permissions'   : ( "Manage DMD", )
             },
           )
          },
        )

    def manage_deletePackable(self, packables=(), REQUEST=None):
        "Delete objects from this ZenPack"
        from sets import Set
        packables = Set(packables)
        for obj in self.packables():
            if obj.getPrimaryUrlPath() in packables:
                self.packables.removeRelation(obj)
        if REQUEST: 
            return self.callZenScreen(REQUEST)
            

from Products.ZenModel.ZenPackLoader import *

def zenPackPath(*parts):
    return os.path.join(os.environ['ZENHOME'], 'Products', *parts)

class ZenPackBase(ZenPack):
    
    zope.interface.implements(interfaces.IZenPack)
    loaders = (ZPLObject(), ZPLReport(), ZPLDaemons(), ZPLSkins())

    def __init__(self, id):
        ZenPack.__init__(self, id)

    def path(self, *args):
        return zenPackPath(self.id, *args)


    def install(self, app):
        for loader in self.loaders:
            loader.load(self, app)


    def remove(self, app):
        for loader in self.loaders:
            loader.unload(self, app)


    def list(self, app):
        result = []
        for loader in self.loaders:
            result.append((loader.name,
                           [item for item in loader.list(self, app)]))
        return result



InitializeClass(ZenPack)
