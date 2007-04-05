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

def eliminateDuplicates(objs):
    def compare(x, y):
        return cmp(x.getPrimaryPath(), y.getPrimaryPath())
    objs.sort(compare)
    result = []
    for obj in objs:
        for alreadyInList in result:
            path = alreadyInList.getPrimaryPath()
            if obj.getPrimaryPath()[:len(path)] == path:
                break
        else:
            result.append(obj)
    return result


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
        ('root', ToOne(ToManyCont, 'Products.ZenModel.DataRoot', 'packs')),
        ("packables", ToMany(ToOne, "Products.ZenModel.ZenPackable", "pack")),
        )

    factory_type_information = (
        { 'immediate_view' : 'viewPackDetail',
          'factory'        : 'manage_addZenPack',
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

    def remove(self, app=None):
        pass

    def manage_deletePackable(self, packables=(), REQUEST=None):
        "Delete objects from this ZenPack"
        from sets import Set
        packables = Set(packables)
        for obj in self.packables():
            if obj.getPrimaryUrlPath() in packables:
                self.packables.removeRelation(obj)
        if REQUEST: 
            return self.callZenScreen(REQUEST)

    def manage_exportPack(self, REQUEST=None):
        "Export the ZenPack to the /export directory"
        from StringIO import StringIO
        from Acquisition import aq_base
        xml = StringIO()
        xml.write("""<?xml version="1.0"?>\n""")
        xml.write("<objects>\n")
        packables = eliminateDuplicates(self.packables())
        for obj in packables:
            obj = aq_base(obj)
            xml.write('<!-- %r -->\n' % (obj.getPrimaryPath(),))
            obj.exportXml(xml,['devices','networks', 'pack'],True)
        xml.write("</objects>\n")
        path = zenPackPath(self.id, 'objects')
        if not os.path.isdir(path):
            os.makeDirs(path)
        objects = file(os.path.join(path, 'objects.xml'), 'w')
        objects.write(xml.getvalue())
        objects.close()
        path = zenPackPath(self.id, 'skins')
        if not os.path.isdir(path):
            os.makeDirs(path)
        init = zenPackPath(self.id, '__init__.py')
        if not os.path.isfile(init):
            fp = file(init, 'w')
            fp.write(
'''
import Globals
from Products.CMFCore.DirectoryView import registerDirectory
registerDirectory("skins", globals())

from Products.ZenModel.ZenPack import ZenPackBase

class ZenPack(ZenPackBase):
    author = %r
    organization = %r
    version = %r

# register any other classes here
''' % (self.author, self.organization, self.version))

            fp.close()
        zenhome = os.getenv('ZENHOME')
        path = os.path.join(zenhome, 'export')
        if not os.path.isdir(path):
            os.makeDirs(path)
        from zipfile import ZipFile, ZIP_DEFLATED
        zf = ZipFile(os.path.join(path, '%s.zip' % self.id), 'w', ZIP_DEFLATED)
        base = zenPackPath()
        for p, ds, fd in os.walk(zenPackPath(self.id)):
            if p.split('/')[-1].startswith('.'): continue
            for f in fd:
                if f.startswith('.'): continue
                if f.endswith('.pyc'): continue
                filename = os.path.join(p, f)
                zf.write(filename, filename[len(base)+1:])
        zf.close()
        if REQUEST:
            REQUEST['message'] = '%s has been exported' % self.id
            return self.callZenScreen(REQUEST)

from Products.ZenModel.ZenPackLoader import *

def zenPackPath(*parts):
    return os.path.join(os.environ['ZENHOME'], 'Products', *parts)

class ZenPackBase(ZenPack):

    author = ''
    organization = ''
    version = '0.1'

    _properites = (
        dict(id='author',       type='string', mode='w'),
        dict(id='organization', type='string', mode='w'),
        dict(id='version',      type='string', mode='w'),
        )        
    
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
