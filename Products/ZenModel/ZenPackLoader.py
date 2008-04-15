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

__doc__='Base Classes for loading gunk in a ZenPack'

import Globals
from Products.ZenReports.ReportLoader import ReportLoader
from Products.ZenUtils.Utils import zenPath

import os
import ConfigParser
import subprocess
import logging
log = logging.getLogger('zen.ZPLoader')

CONFIG_FILE = 'about.txt'
CONFIG_SECTION_ABOUT = 'about'

def findFiles(pack, directory, filter=None):
    result = []
    for p, ds, fs in os.walk(pack.path(directory)):
        if not os.path.split(p)[-1].startswith('.'):
            for f in fs:
                if filter is None or filter(f):
                    result.append(os.path.join(p, f))
    return result

def findDirectories(pack, directory):
    result = []
    for p, ds, fs in os.walk(pack.path(directory)):
        if not os.path.split(p)[-1].startswith('.'):
            for d in ds:
                result.append(os.path.join(p, d))
    return result

def branchAfter(filename, directory, prefix = ""):
    "return the branch after the given directory name"
    path = filename.split('/')
    return prefix + '/'.join(path[path.index(directory)+1:])


class ZenPackLoader:

    name = "Set This Name"

    def load(self, pack, app):
        """Load things from the ZenPack and put it
        into the app"""

    def unload(self, pack, app, leaveObjects=False):
        """Remove things from Zenoss defined in the ZenPack"""

    def list(self, pack, app):
        "List the items that would be loaded from the given (unpacked) ZenPack"

    def upgrade(self, pack, app):
        "Run an upgrade on an existing pack"

from xml.sax import make_parser

class ZPLObject(ZenPackLoader):

    name = "Objects"

    def load(self, pack, app):
        from Products.ZenRelations.ImportRM import ImportRM
        class AddToPack(ImportRM):
            def endElement(self, name):
                if name == 'object':
                    obj = self.objstack[-1]
                    log.debug('Now adding %s', obj.getPrimaryUrlPath())
                    try:
                        obj.buildRelations()
                        obj.removeRelation('pack')
                        obj.addRelation('pack', pack)
                    except Exception, ex:
                        log.exception("Error adding pack to %s",
                                      obj.getPrimaryUrlPath())

                ImportRM.endElement(self, name)
        importer = AddToPack(noopts=True, app=app)
        importer.options.noindex = True
        for f in self.objectFiles(pack):
            log.info("Loading %s", f)
            importer.loadObjectFromXML(xmlfile=f)


    def parse(self, filename, handler):
        parser = make_parser()
        parser.setContentHandler(handler)
        parser.parse(open(filename))


    def unload(self, pack, app, leaveObjects=False):
        if leaveObjects:
            return
        from Products.ZenRelations.Exceptions import ObjectNotFound
        dmd = app.zport.dmd
        objs = pack.packables()
        objs.sort(lambda x, y: cmp(x.getPrimaryPath(), y.getPrimaryPath()))
        objs.reverse()
        for obj in objs:
            path = obj.getPrimaryPath()
            path, id = path[:-1], path[-1]
            obj = dmd.getObjByPath(path)
            if len(path) > 3:           # leave /Services, /Devices, etc.
                try:
                    try:
                        obj._delObject(id)
                    except ObjectNotFound:
                        obj._delOb(id)
                except (AttributeError, KeyError), ex:
                    log.warning("Unable to remove %s on %s", id,
                                '/'.join(path))

    def list(self, pack, unused):
        return [obj.getPrimaryUrlPath() for obj in pack.packables()]


    def objectFiles(self, pack):
        def isXml(f): return f.endswith('.xml')
        return findFiles(pack, 'objects', isXml)


class ZPLReport(ZPLObject):

    name = "Reports"

    def load(self, pack, app):
        class HookReportLoader(ReportLoader):
            def loadFile(self, root, id, fullname):
                rpt = ReportLoader.loadFile(self, root, id, fullname)
                rpt.addRelation('pack', pack)
                return rpt
        rl = HookReportLoader(noopts=True, app=app)
        rl.options.force = True
        rl.loadDirectory(pack.path('reports'))

    def upgrade(self, pack, app):
        self.unload(pack, app)
        self.load(pack, app)

    def list(self, pack, unused):
        return [branchAfter(r, 'reports') for r in findFiles(pack, 'reports')]


class ZPLDaemons(ZenPackLoader):

    name = "Daemons"

    extensionsToIgnore = ('.svn-base', '.pyc' '~')
    def filter(self, f):
        for ext in self.extensionsToIgnore:
            if f.endswith(ext):
                return False
        return True


    def binPath(self, daemon):
        return zenPath('bin', os.path.basename(daemon))


    def _genConfFile(self, pack):
        """
        Attempt to generate a conf file for any daemons.
        """
        # We just go on with business, not waiting for this to finish
        # nor caring if it throws an exception.  The conf file is nice
        # to provide, but not important.
        try:
            subprocess.Popen(zenPath('bin', 'create_sample_config.sh'),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            cwd=pack.path())
        except OSError:
            pass


    def load(self, pack, unused):
        for fs in findFiles(pack, 'daemons', filter=self.filter):
            os.chmod(fs, 0755)
            path = self.binPath(fs)
            if os.path.lexists(path):
                os.remove(path)
            os.symlink(fs, path)
        self._genConfFile(pack)


    def upgrade(self, pack, app):
        self.unload(pack, app)
        self.load(pack, app)


    def unload(self, pack, unused, leaveObjects=False):
        for fs in findFiles(pack, 'daemons', filter=self.filter):
            try:
                os.remove(self.binPath(fs))
            except OSError:
                pass

    def list(self, pack, unused):
        return [branchAfter(d, 'daemons')
                for d in findFiles(pack, 'daemons', filter=self.filter)]


class ZPLBin(ZenPackLoader):

    name = "Bin"

    extensionsToIgnore = ('.svn-base', '.pyc' '~')
    def filter(self, f):
        for ext in self.extensionsToIgnore:
            if f.endswith(ext):
                return False
        return True

    def load(self, pack, unused):
        for fs in findFiles(pack, 'bin', filter=self.filter):
            os.chmod(fs, 0755)

    def upgrade(self, pack, app):
        self.unload(pack, app)
        self.load(pack, app)

    def list(self, pack, unused):
        return [branchAfter(d, 'bin')
                for d in findFiles(pack, 'bin', filter=self.filter)]


class ZPLLibExec(ZenPackLoader):

    name = "LibExec"

    extensionsToIgnore = ('.svn-base', '.pyc' '~')
    def filter(self, f):
        for ext in self.extensionsToIgnore:
            if f.endswith(ext):
                return False
        return True

    def load(self, pack, unused):
        for fs in findFiles(pack, 'libexec', filter=self.filter):
            os.chmod(fs, 0755)

    def upgrade(self, pack, app):
        self.unload(pack, app)
        self.load(pack, app)

    def list(self, pack, unused):
        return [branchAfter(d, 'libexec')
                for d in findFiles(pack, 'libexec', filter=self.filter)]


class ZPLModelers(ZenPackLoader):

    name = "Modeler Plugins"


    def list(self, pack, unused):
        return [branchAfter(d, 'plugins')
                for d in findFiles(pack, 'modeler/plugins')]


class ZPLSkins(ZenPackLoader):

    name = "Skins"


    def load(self, pack, app):
        from Products.ZenUtils.Skins import registerSkin
        registerSkin(app.zport.dmd, pack.path(''))


    def upgrade(self, pack, app):
        self.unload(pack, app)
        return self.load(pack, app)


    def unload(self, pack, app, leaveObjects=False):
        from Products.ZenUtils.Skins import unregisterSkin
        unregisterSkin(app.zport.dmd, pack.path(''))


    def list(self, pack, unused):
        return [branchAfter(d, 'skins') for d in findDirectories(pack, 'skins')]


class ZPLDataSources(ZenPackLoader):

    name = "DataSources"


    def list(self, pack, unused):
        return [branchAfter(d, 'datasources')
                for d in findFiles(pack, 'datasources',
                lambda f: not f.endswith('.pyc') and f != '__init__.py')]



class ZPLLibraries(ZenPackLoader):

    name = "Libraries"


    def list(self, pack, unused):
        d = pack.path('lib')
        if os.path.isdir(d):
            return [l for l in os.listdir(d)]
        return []

class ZPLAbout(ZenPackLoader):

    name = "About"

    def getAttributeValues(self, pack):
        about = pack.path(CONFIG_FILE)
        result = []
        if os.path.exists(about):
            parser = ConfigParser.SafeConfigParser()
            parser.read(about)
            result = []
            for key, value in parser.items(CONFIG_SECTION_ABOUT):
                try:
                    value = eval(value)
                except:
                    # Blanket exception catchers like this are evil.
                    pass
                result.append((key, value))
        return result


    def load(self, pack, unused):
        for name, value in self.getAttributeValues(pack):
            setattr(pack, name, value)


    def upgrade(self, pack, app):
        self.load(pack, app)


    def list(self, pack, unused):
        return [('%s %s' % av) for av in self.getAttributeValues(pack)]
