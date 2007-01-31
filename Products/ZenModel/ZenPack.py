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
    _relations =  (
        ('root', ToOne(ToManyCont, 'DataRoot', 'packs')),
        )

from Products.ZenModel.ZenPackLoader import *

def zenPackPath(*parts):
    return os.path.join(os.environ['ZENHOME'], 'Products', *parts)

class ZenPackBase(ZenPack):
    
    zope.interface.implements(interfaces.IZenPack)
    loaders = (ZPLObject(), ZPLReport(), ZPLDaemons())

    def __init__(self, id):
        ZenPack.__init__(self, id)

    def path(self, *args):
        return zenPackPath(self.id, *args)


    def install(self, cmd):
        for loader in self.loaders:
            loader.load(self, cmd)
        transaction.commit()


    def remove(self, cmd):
        for loader in self.loaders:
            loader.unload(self, cmd)


    def list(self, cmd):
        result = []
        for loader in self.loaders:
            result.append((loader.name,
                           [item for item in loader.list(self, cmd)]))
        return result

InitializeClass(ZenPack)
