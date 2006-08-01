import sys
import os
import glob
from sets import Set
import pprint

import Globals
import transaction


from Products.ZenUtils.ZCmdBase import ZCmdBase

import re
DEFINITIONS=re.compile(r'([A-Za-z-0-9]+) +DEFINITIONS *::= *BEGIN')
DEPENDS=re.compile(r'FROM *([A-Za-z-0-9]+)')

def walk(*dirs):
    for dir in dirs:
        for dirname, _, filenames in os.walk(dir):
            for f in filenames:
                yield os.path.join(dirname, f)

class DependencyMap:
    def __init__(self):
        self.fileMap = {}
        self.depMap = {}

    def add(self, filename, name, dependencies):
        if not self.depMap.has_key(name):
            self.fileMap[filename] = name
            self.depMap[name] = (filename, dependencies)

    def getName(self, filename):
        return self.fileMap.get(filename, None)

    def getDependencies(self, name):
        return self.depMap.get(name, None)


class zenmib(ZCmdBase):

    def parse(self, mibfile):
        fp = open(mibfile)
        mib = fp.read()
        fp.close()
        parts = mib.split('OBJECT IDENTIFIER', 1)
        match = DEFINITIONS.search(parts[0])
        if not match: return None, []
        name = match.group(1)
        depends = []
        start = match.end(0)
        while 1:
            match = DEPENDS.search(parts[0], start)
            if not match: break
            depends.append(match.group(1))
            start = match.end(0)
        return name, depends
        

    def dependencies(self, filenames):
        result = DependencyMap()
        for filename in filenames:
            defines, depends = self.parse(filename)
            if defines == None:
                self.log.info("Skipping file %s", filename)
            else:
                result.add(filename, defines, depends)
        return result

    def generateDependenciesForSMIDump(self, filename, depMap):
        deps = []
        name = depMap.getName(filename)
        if not name:
            return ''
        def recurse(name):
            fileAndDeps = depMap.getDependencies(name)
            if not fileAndDeps:
                self.log.info("Unable to find a file providing the MIB %s",
                              name)
                return
            f, d = fileAndDeps
            if f and f not in deps:
                deps.append(f)
            for n in d:
                recurse(n)
        recurse(name)
        if deps[1:]:
            return ' -p "' + '" -p "'.join(deps[1:]) + '"'
        return ''
    
    MIB_MOD_ATTS = ('language', 'contact', 'description')

    def load1(self, mibs, mibname, depmap):
        result = {}
        self.log.debug("%s", mibname.split('/')[-1])
        dependencies = self.generateDependenciesForSMIDump(mibname, depmap)
        dump = 'smidump -fpython %s "%s" 2>/dev/null' % (dependencies, mibname)
        self.log.debug('running %s', dump)
        exec os.popen(dump) in result
        mib = result.get('MIB', None)
        if mib:
            modname = mib['moduleName']
            #mod = mibs.findMibModule(modname)
            mod = None
            if mod:
                self.log.warn("skipping %s already loaded", modname)
                return
            mod = mibs.createMibModule(modname, self.options.path)
            for key, val in mib[modname].items():
                if key in self.MIB_MOD_ATTS:
                    setattr(mod, key, val)
            if mib.has_key('nodes'):
                for name, values in mib['nodes'].items():
                    mod.createMibNode(name, **values) 
            if mib.has_key('notifications'):
                for name, values in mib['notifications'].items():
                    mod.createMibNotification(name, **values) 
            self.log.info("Loaded mib %s", modname)
            if not self.options.nocommit: transaction.commit() 
        else:
            self.log.error("Failed to load mib: %s", mibname)
            if self.options.debug:
                msg = os.popen('smidump -fpython %s 2>&1' % mibname).read()
                self.log.error("Error: %s", msg)

    def load(self):

        smimibdir = os.path.join(os.environ['ZENHOME'], 'share/mibs')
        ietf, iana, irtf, tubs, site = \
              map(lambda x: os.path.join(smimibdir, x),
                  'ietf iana irtf tubs site'.split())

        if len(self.args) > 0:
            mibnames = self.args
            depMap = self.dependencies(list(walk(ietf, iana, irtf, tubs))
                                       + mibnames)
        else:
            depMap = self.dependencies(walk(ietf, iana, irtf, tubs, site))
            mibnames = glob.glob(os.path.join(smimibdir, 'site', '*'))

        mibs = self.dmd.Mibs
        for mibname in mibnames:
            try:
                self.load1(mibs, mibname, depMap)
            except (SystemExit, KeyboardInterrupt): raise
            except Exception, ex:
                self.log.exception("Failed to load mib: %s", mibname)

        
    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--path', 
                               dest='path',default="/",
                               help="path to load mib into")
        self.parser.add_option('--nocommit', action='store_true',
                               dest='nocommit',default=False,
                               help="don't commit after loading")
        self.parser.add_option('--debug', action='store_true',
                               dest='debug',default=False,
                               help="print diagnostic information")


if __name__ == '__main__':
    import sys
    zm = zenmib()
    zm.load()
