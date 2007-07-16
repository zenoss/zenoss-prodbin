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
import zope.interface

from Globals import InitializeClass
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenModel import interfaces
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.Utils import importClass
from Products.ZenModel.migrate import Migrate
from Products.ZenUtils.Version import getVersionTupleFromString
from Products.ZenModel.migrate.Migrate import Version
from Products.ZenModel.ZenPackLoader import *

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


class ZenPackMigration:
    version = Version(0, 0, 0)
    
    def migrate(self, pack): pass
    
    def recover(self, pack): pass


class ZenPack(ZenModelRM):
    '''The root of all ZenPacks: has no implementation,
    but sits here to be the target of the Relation'''

    objectPaths = None
    author = ''
    organization = ''
    url = ''
    version = '0.1'

    requires = ()

    loaders = (ZPLObject(), ZPLReport(), ZPLDaemons(), ZPLSkins(),
                ZPLDataSources(), ZPLLibraries(), ZPLAbout())
                
    _properties = ZenModelRM._properties + (
        {'id':'objectPaths','type':'lines','mode':'w'},
        {'id':'author', 'type':'string', 'mode':'w'},
        {'id':'organization', 'type':'string', 'mode':'w'},
        {'id':'version', 'type':'string', 'mode':'w'},
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


    def path(self, *args):
        return zenPackPath(self.id, *args)


    def install(self, app):
        for loader in self.loaders:
            loader.load(self, app)


    def upgrade(self, app):
        for loader in self.loaders:
            loader.upgrade(self, app)
        self.migrate()


    def remove(self, app):
        for loader in self.loaders:
            loader.unload(self, app)

    def migrate(self):
        import sys
        instances = []
        # find all the migrate modules
        root = self.path("migrate")
        for p, ds, fs in os.walk(root):
            for f in fs:
                if f.endswith('.py') and not f.startswith("__"):
                    path = os.path.join(p[len(root) + 1:], f)
                    log.debug("Loading %s", path)
                    sys.path.insert(0, p)
                    try:
                        try:
                            c = importClass(path[:-3].replace("/", "."))
                            instances.append(c())
                        finally:
                            sys.path.remove(p)
                    except ImportError, ex:
                        log.exception("Problem loading migration step %s", path)
        # sort them by version number
        instances.sort()
        # install those that are newer than our pack version
        current = getVersionTupleFromString(self.version)
        recover = []
        try:
            for instance in instances:
                if instance.version >= current:
                    recover.append(instance)
                    instance.migrate(self)
        except Exception, ex:
            # give the pack a chance to recover from problems
            recover.reverse()
            for r in recover:
                r.recover()
            raise ex


    def list(self, app):
        result = []
        for loader in self.loaders:
            result.append((loader.name,
                           [item for item in loader.list(self, app)]))
        return result


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
        
        # Write out packable objects
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
            os.mkdir(path, 0750)
        objects = file(os.path.join(path, 'objects.xml'), 'w')
        objects.write(xml.getvalue())
        objects.close()
        
        # Create skins dir if not there
        path = zenPackPath(self.id, 'skins')
        if not os.path.isdir(path):
            os.makeDirs(path, 0750)
            
        # Create __init__.py
        init = zenPackPath(self.id, '__init__.py')
        if not os.path.isfile(init):
            fp = file(init, 'w')
            fp.write(
'''
import Globals
from Products.CMFCore.DirectoryView import registerDirectory
registerDirectory("skins", globals())
''')
            fp.close()
        
        # Create about.txt
        about = zenPackPath(self.id, CONFIG_FILE)
        values = {}
        parser = ConfigParser.SafeConfigParser()
        if os.path.isfile(about):
            try:
                parser.read(about)
                values = dict(parser.items(CONFIG_SECTION_ABOUT))
            except ConfigParser.Error:
                pass
        values.update(dict([(p[id], str(getattr(self, p[id], '')))
                        for p in self._properties]))
        fp = file(about, 'w')
        try:
            parser.write(fp)
        finally:
            fp.close()

        # Create the zip file
        zenhome = os.getenv('ZENHOME')
        path = os.path.join(zenhome, 'export')
        if not os.path.isdir(path):
            os.makeDirs(path, 0750)
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


    def getDataSourceClasses(self):
        dsClasses = []
        for path, dirs, files in os.walk(self.path('datasources')):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                if not f.startswith('.') \
                        and f.endswith('.py') \
                        and not f == '__init__.py':
                    parts = path.split('/') + [f[:-3]]
                    parts = parts[parts.index('Products'):]
                    dsClasses.append(importClass('.'.join(parts)))
        return dsClasses


def zenPackPath(*parts):
    return os.path.join(os.environ['ZENHOME'], 'Products', *parts)


# ZenPackBase is here for backwards compatibility with older installed
# zenpacks that used it.  ZenPackBase was rolled into ZenPack when we
# started using about.txt files instead of ZenPack subclasses to set
# zenpack metadata.
ZenPackBase = ZenPack

InitializeClass(ZenPack)
