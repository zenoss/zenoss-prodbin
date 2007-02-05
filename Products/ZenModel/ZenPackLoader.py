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
import logging
log = logging.getLogger('zen.ZPLoader')

def findFiles(pack, directory, filter=None):
    result = []
    for p, ds, fs in os.walk(pack.path(directory)):
        if not os.path.split(p)[-1].startswith('.'):
            for f in fs:
                if filter is None or filter(f):
                    result.append(os.path.join(p, f))
    return result

def branchAfter(filename, directory, prefix = ""):
    "return the branch after the given directory name"
    path = filename.split('/')
    return prefix + '/'.join(path[path.index(directory)+1:])


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

class PathTracker(ContentHandler):
    "Keep the object path as we navigate XML"
    def __init__(self):
        self.stack = ['']
    def startElement(self, name, attrs):
        id = attrs.get('id', None)
        if id:
            if self.stack[-1]:
                id = self.stack[-1] + '/' + id
        else:
            id = self.stack[-1]
        self.stack.append(id)
    def endElement(self, name):
        id = self.stack.pop()
    def path(self):
        return self.stack[-1]

class ZPLObject(ZenPackLoader):

    name = "Objects"

    def load(self, pack, cmd):
        from Products.ZenRelations.ImportRM import ImportRM
        importer = ImportRM(noopts=True, app=cmd.app)
        importer.options.noindex = True
        for f in self.objectFiles(pack):
            log.info("Loading %s", f)
            importer.loadObjectFromXML(xmlfile=f)

    def parse(self, filename, handler):
        parser = make_parser()
        parser.setContentHandler(handler)
        parser.parse(open(filename))
        

    def unload(self, pack, cmd):
        class Deleter(PathTracker):
            def endElement(self, name):
                PathTracker.endElement(self, name)
                id = self.path()
                if name == 'object' and id:
                    log.info("Removing %s", id)
                    path = id.split('/')
                    id = path.pop()
                    try:
                        obj = getObjByPath(cmd.app, path)
                        obj._delObject(id)
                    except (AttributeError, KeyError), ex:
                        log.warning("Unable to remove %s on %s", id,
                                    '/'.join(path))
        for f in self.objectFiles(pack):
            self.parse(f, Deleter())

    def list(self, pack, cmd):
        objs = []
        class Collector(PathTracker):
            def startElement(self, name, attrs):
                PathTracker.startElement(self, name, attrs)
                if name == 'object' and self.path():
                    objs.append(self.path())
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
        rl.options = cmd.options
        rl.loadDirectory(pack.path('reports'))

    def unload(self, pack, cmd):
        rl = ReportLoader(noopts=True, app=cmd.app)
        rl.unloadDirectory(pack.path('reports'))

    def list(self, pack, cmd):
        def rpt(f):
            return f.endswith('.rpt')
        return [branchAfter(fs[:-4], 'reports', "/zport/dmd/Reports/")
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

