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
__doc__ = "Manage ZenPacks"

import Globals
from Products.ZenModel.ZenPack import ZenPackBase, zenPackPath
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.ZenUtils.Utils import cleanupSkins
import transaction

import os, sys

class ZenPackCmd(ZenScriptBase):
    "Manage ZenPacks"

    def run(self):
        "Execute the user's request"
        self.connect()
        if self.options.installPackName:
            if os.path.isfile(self.options.installPackName):
                packName = self.extract(self.options.installPackName)
            elif os.path.isdir(self.options.installPackName):
                packName = self.copyDir(self.options.installPackName)
            else:
                self.stop('%s does not appear to be a valid file or directory.')
            self.install(packName)

        elif self.options.removePackName:
            self.remove(self.options.removePackName)

        elif self.options.list:
            for zp in self.dmd.packs():
                f = sys.modules[zp.__module__].__file__
                if f.endswith('.pyc'):
                    f = f[:-1]
                print '%s (%s)' % (zp.id, f)
                for extensionType, lst in zp.list(self.app):
                    print '  %s:' % extensionType
                    for item in lst:
                        print '    %s' % item
            
        transaction.commit()


    def install(self, packName):
                    
        if self.options.force:
            try:
                self.dmd.packs._delObject(packName)
            except AttributeError:
                pass
        try:
            zp = self.dmd.packs._getOb(packName)
            self.stop('A ZenPack "%s" already exists' % packName)
        except AttributeError:
            pass
        try:
            module =  __import__('Products.' + packName, globals(), {}, [''])
            zp = module.ZenPack(packName)
        except (ImportError, AttributeError), ex:
            self.log.debug("Unable to find custom ZenPack (%s), "
                           "defaulting to ZenPackBase",
                           ex)
            zp = ZenPackBase(packName)
        self.dmd.packs._setObject(packName, zp)
        zp.install(self.app)
        transaction.commit()


    def remove(self, packName):
        self.log.debug('Removing Pack "%s"' % packName)
        zp = None
        try:
            zp = self.dmd.packs._getOb(packName)
        except AttributeError, ex:
            self.stop('There is no ZenPack named "%s"' % packName)
        zp.remove(self.app)
        self.dmd.packs._delObject(packName)
        root = zenPackPath(packName)
        for p, ds, fs in os.walk(root, topdown=False):
            for f in fs:
                self.log.debug('Removing file "%s"' % f)
                os.remove(os.path.join(p, f))
            for d in ds:
                path = os.path.join(p, d)
                if os.path.islink(path):
                    self.log.debug('Removing link "%s"' % d)
                    os.remove(path)
                else:
                    self.log.debug('Removing dir "%s"' % d)
                    os.rmdir(path)
        os.rmdir(root)
        cleanupSkins(self.dmd)


    def extract(self, fname):
        "Unpack a ZenPack, and return the name"
        from zipfile import ZipFile
        if not os.path.isfile(fname):
            self.stop('Unable to open file "%s"' % fname)
        zf = ZipFile(fname)
        name = zf.namelist()[0]
        packName = name.split('/')[0]
        root = zenPackPath(packName)
        if os.path.isdir(root) and not self.options.force:
            self.stop("%s already exists" % root)
        self.log.debug('Extracting ZenPack "%s"' % packName)
        for name in zf.namelist():
            fullname = os.path.join(os.environ['ZENHOME'], 'Products', name)
            self.log.debug('Extracting %s' % name)
            if name.find('/.svn') > -1: continue
            if name.endswith('~'): continue
            if name.endswith('/'):
                if not os.path.exists(fullname):
                    os.makedirs(fullname)
            else:
                base = os.path.dirname(fullname)
                if not os.path.isdir(base):
                    os.makedirs(base)
                file(fullname, 'wb').write(zf.read(name))
        return packName
        
        
    def copyDir(self, srcDir):
        '''Copy an unzipped zenpack to the appropriate location.
        Return the name.
        '''
        # Normalize srcDir to not end with slash
        if srcDir.endswith('/'):
            srcDir = srcDir[:-1]
        
        if not os.path.isdir(srcDir):
            self.stop('Specified directory does not appear to exist: %s' %
                        srcDir)
        
        # Determine name of pack and it's destination directory                
        packName = os.path.split(srcDir)[1]
        root = zenPackPath(packName)
        
        # Continue without copying if the srcDir is already in Products
        if os.path.exists(root) and os.path.samefile(root, srcDir):
            self.log.debug('Directory already in $ZENHOME/Products,'
                            ' not copying.')
            return packName
        
        # destSrc isn't in Products, but a directory for this pack
        # already exists there.  Panic unless --force.
        if os.path.isdir(root) and not self.options.force:
            self.stop('%s already exists' % root)
            
        # Copy the source dir over to Products
        self.log.debug('Copying %s' % packName)
        #result = os.system('cp -r %s $ZENHOME/Products/' % srcDir)
        result = os.system('rsync -rlC %s $ZENHOME/Products' % srcDir)
        if result == -1:
            self.stop('Error copying %s to $ZENHOME/Products' % srcDir)
        
        return packName
        

    def stop(self, why):
        self.log.error("zenpack stopped: %s", why)
        import sys
        sys.exit(1)
        
    
    def buildOptions(self):
        self.parser.add_option('--install',
                               dest='installPackName',
                               default=None,
                               help="name of the pack to install")
        self.parser.add_option('--remove',
                               dest='removePackName',
                               default=None,
                               help="name of the pack to remove")
        self.parser.add_option('--list',
                               dest='list',
                               action="store_true",
                               default=False,
                               help="name of the pack to remove")
        self.parser.add_option('--force',
                               dest='force',
                               action="store_true",
                               default=False,
                               help="ignore an existing pack installation")
        ZenScriptBase.buildOptions(self)

if __name__ == '__main__':
    zp = ZenPackCmd()
    zp.run()
