import zope.interface

from Globals import InitializeClass
from Products.ZenModel import interfaces
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.Utils import getObjByPath

import transaction

import os

def zenPackPath(*parts):
    return os.path.join(os.environ['ZENHOME'], 'Products', *parts)

class ZenPack(ZenModelRM):
    '''The root of all ZenPacks: has no implementation,
    but sits here to be the target of the Relation'''
    _relations =  (
        ('root', ToOne(ToManyCont, 'DataRoot', 'packs')),
        )

class ZenPackBase(ZenPack):
    
    zope.interface.implements(interfaces.IZenPack)

    def __init__(self, id):
        ZenPack.__init__(self, id)


    def install(self, cmd):
        self.loadObjects(cmd)
        self.loadReportPages()
        def executable(f):
            os.chmod(f, 0755)
        map(executable, self.daemons())


    def remove(self, cmd):
        self.removeObjects(cmd)
        self.removeReportPages()


    def _findFiles(self, directory, filter=None):
        return [os.path.join(p, f)
                for p, ds, fs in os.walk(zenPackPath(self.id, directory))
                for f in fs
                if filter and filter(f)]
                    

    def daemons(self):
        return self._findFiles('daemons')


    def modelers(self):
        pass


    def reports(self):
        pass


    def objectFiles(self):
        def isXml(f): return f.endswith('.xml')
        return self._findFiles('objects', isXml)


    def loadObjects(self, cmd):
        "load data from xml files"
        from Products.ZenRelations.ImportRM import ImportRM
        importer = ImportRM(noopts=True, app=cmd.app)
        importer.options.noindex = True
        for f in self.objectFiles():
            importer.loadObjectFromXML(xmlfile=f)
        transaction.commit()


    def removeObjects(self, cmd):
        "remove objects that would come from xml"
        from xml.sax import make_parser, saxutils
        from xml.sax.handler import ContentHandler
        class Deleter(ContentHandler):
            def __init__(self):
                self.stack = []
            def startElement(self, name, attrs):
                if name == 'object':
                    self.stack.append(attrs.get('id', None))
            def endElement(self, name):
                if name == 'object':
                    id = self.stack.pop()
                    if id:
                        path = id.split('/')
                        id = path.pop()
                        obj = getObjByPath(cmd.app, path)
                        obj._delObject(id)
        for f in self.objectFiles():
            parser = make_parser()
            parser.setContentHandler(Deleter())
            parser.parse(open(f))


    def loadReportPages(self):
        "load pages in using ReportLoader.py"

    def removeReportPages(self):
        "remove reports in our report tree"

    
InitializeClass(ZenPack)
