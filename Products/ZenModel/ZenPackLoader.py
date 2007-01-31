##############################################################################
#
#   Copyright (c) 2007 Zenoss, Inc.. 
#
###############################################################################

__doc__='Base Classes for loading gunk in a ZenPack'

import Globals
from Products.ZenReports.ReportLoader import ReportLoader
from Products.ZenUtils.Utils import getObjByPath

import os

def findFiles(pack, directory, filter=None):
    return [os.path.join(p, f)
            for p, ds, fs in os.walk(pack.path(directory))
            for f in fs
            if filter is None or filter(f)]

def branchAfter(filename, directory):
    "return the branch after the given directory name"
    path = filename.split('/')
    return '/'.join(path[path.index(directory):])


class ZenPackLoader:

    name = "Set This Name"

    def load(self, pack, cmd):
        """Load things from the ZenPack and put it 
        into the app available on cmd"""

    def unload(self, pack, cmd):
        """Remove things from Zenoss defined in the ZenPack"""

    def list(self, pack, cmd):
        "List the items that would be loaded from the given (unpacked) ZenPack"

from xml.sax import saxutils, make_parser
from xml.sax.handler import ContentHandler

class ZPLObject(ZenPackLoader):

    name = "Objects"

    def load(self, pack, cmd):
        from Products.ZenRelations.ImportRM import ImportRM
        importer = ImportRM(noopts=True, app=cmd.app)
        importer.options.noindex = True
        for f in self.objectFiles(pack):
            importer.loadObjectFromXML(xmlfile=f)

    def parse(self, filename, handler):
        parser = make_parser()
        parser.setContentHandler(handler)
        parser.parse(open(filename))
        

    def unload(self, pack, cmd):
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
        for f in self.objectFiles(pack):
            self.parse(f, Deleter())

    def list(self, pack, cmd):
        objs = []
        class Collector(ContentHandler):
            def startElement(self, name, attrs):
                if name == 'object':
                    objs.append(attrs.get('id', None))
        for f in self.objectFiles(pack):
            self.parse(f, Collector())
        return objs
        

    def objectFiles(self, pack):
        def isXml(f): return f.endswith('.xml')
        return findFiles(pack, 'objects', isXml)


class ZPLReport(ZenPackLoader):

    name = "Reports"

    def load(self, pack, cmd):
        rl = ReportLoader(noopts=True, app=cmd.app)
        rl.loadDirectory(pack.path('reports'))

    def unload(self, pack, cmd):
        rl = ReportLoader(noopts=True, app=cmd.app)
        rl.unloadDirectory(pack.path('reports'))

    def list(self, pack, cmd):
        def rpt(f):
            return f.endswith('.rpt')
        return [branchAfter(fs[:-4], 'reports')
                for fs in findFiles(pack, 'reports', rpt)]


class ZPLDaemons(ZenPackLoader):

    name = "Daemons"

    def load(self, pack, cmd):
        for fs in findFiles(pack, 'daemons'):
            os.chmod(fs, 0755)

    def list(self, pack, cmd):
        return [branchAfter(d, 'daemons')
                for d in findFiles(pack, 'daemons')]


class ZPLModelers(ZenPackLoader):

    name = "Modeler Plugins"

    def list(self, pack, cmd):
        return [branchAfter(d, 'plugins')
                for d in findFiles(pack, 'modeler/plugins')]

