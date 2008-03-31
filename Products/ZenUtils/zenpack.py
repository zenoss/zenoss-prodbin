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
from Products.ZenModel.ZenPack import ZenPack, ZenPackException, \
                                        ZenPackNeedMigrateException
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.ZenUtils.Utils import cleanupSkins, zenPath
import transaction
from zipfile import ZipFile
from StringIO import StringIO
import ConfigParser
import Products.ZenModel.ZenPackLoader as ZPL
from Products.ZenModel.ZenPackLoader import CONFIG_FILE, CONFIG_SECTION_ABOUT
import os, sys
import ZenPackCmd as EggPackCmd

class ZenPackCmd(ZenScriptBase):
    "Manage ZenPacks"
    

    def run(self):
        "Execute the user's request"
        
        if self.options.installPackName:
            eggInstall = (self.options.installPackName.lower().endswith('.egg')
                or os.path.exists(os.path.join(self.options.installPackName,
                                                'setup.py')))                    

        # files-only just lays the files down and doesn't "install"
        # them into zeo
        class ZPProxy:
            def __init__(self, zpId):
                self.id = zpId
            def path(self, *parts):
                return zenPath('Products', self.id, *parts)
        if self.options.installPackName and self.options.filesOnly:
            if eggInstall:
                return  EggPackCmd.InstallZenPack(None,
                            self.options.installPackName,
                                filesOnly=True)
            packName = self.extract(self.options.installPackName)
            proxy = ZPProxy(packName)
            for loader in (ZPL.ZPLDaemons(), ZPL.ZPLBin(), ZPL.ZPLLibExec()):
                loader.load(proxy, None)
            return
        if self.options.removePackName and self.options.filesOnly:
            # Remove files-only is not yet supported for egg zenpacks
            # todo
            proxy = ZPProxy(self.options.removePackName)
            for loader in (ZPL.ZPLDaemons(), ZPL.ZPLBin(), ZPL.ZPLLibExec()):
                loader.unload(proxy, None)
            os.system('rm -rf %s' % zenPath('Products', 
                                            self.options.removePackName))
            return
            
            
            
        self.connect()

        if not getattr(self.dmd, 'ZenPackManager', None):
            raise ZenPackNeedMigrateException('Your Zenoss database appears'
                ' to be out of date. Try running zenmigrate to update.')

        if self.options.installPackName:
            if eggInstall:
                return EggPackCmd.InstallEggAndZenPack(
                    self.dmd,
                    self.options.installPackName,
                    develop=self.options.develop,
                    link=self.options.link,
                    filesOnly=False)
            if not self.preInstallCheck():
                self.stop('%s not installed' % self.options.installPackName)
            if os.path.isfile(self.options.installPackName):
                packName = self.extract(self.options.installPackName)
            elif os.path.isdir(self.options.installPackName):
                if self.options.link:
                    packName = self.linkDir(self.options.installPackName)
                else:
                    packName = self.copyDir(self.options.installPackName)
            else:
                self.stop('%s does not appear to be a valid file or directory.'
                          % self.options.installPackName)
            # We want to make sure all zenpacks have a skins directory and that it
            # is registered. The zip file may not contain a skins directory, so we
            # create one here if need be.  The directory should be registered
            # by the zenpack's __init__.py and the skin should be registered
            # by ZPLSkins loader.
            skinsSubdir = zenPath('Products', packName, 'skins', packName)
            if not os.path.exists(skinsSubdir):
                os.makedirs(skinsSubdir, 0750)
            self.install(packName)

        elif self.options.removePackName:
            pack = self.dmd.ZenPackManager.packs._getOb(
                                        self.options.removePackName, None)
            if not pack:
                raise ZenPackException('ZenPack %s is not installed.' %
                                        self.options.removePackName)
            if pack.isEggPack():
                return EggPackCmd.RemoveZenPack(self.dmd,
                                                self.options.removePackName)
            self.remove(self.options.removePackName)

        elif self.options.list:
            for zp in self.dmd.ZenPackManager.packs():
                print('%s (%s)' % (zp.id, 
                                zp.isEggPack() and zp.eggPath() or zp.path()))
            
        transaction.commit()


    def preInstallCheck(self):
        ''' Check that prerequisite zenpacks are installed.
        Return True if no prereqs specified or if they are present.
        False otherwise.
        '''
        if os.path.isfile(self.options.installPackName):
            zf = ZipFile(self.options.installPackName)
            for name in zf.namelist():
                if name.endswith == '/%s' % CONFIG_FILE:
                    sio = StringIO(zf.read(name))
            else:
                return True
        else:
            name = os.path.join(self.options.installPackName, CONFIG_FILE)
            if os.path.isfile(name):
                fp = open(name)
                sio = StringIO(fp.read())
                fp.close()
            else:
                return True
                
        parser = ConfigParser.SafeConfigParser()
        parser.readfp(sio, name)
        if parser.has_section(CONFIG_SECTION_ABOUT) \
            and parser.has_option(CONFIG_SECTION_ABOUT, 'requires'):
            requires = eval(parser.get(CONFIG_SECTION_ABOUT, 'requires'))
            if not isinstance(requires, list):
                requires = [zp.strip() for zp in requires.split(',')]
            missing = [zp for zp in requires 
                        if zp not in self.dataroot.packs.objectIds()]
            if missing:
                self.log.error('ZenPack %s was not installed because'
                                % self.options.installPackName
                                + ' it requires the following ZenPack(s): %s'
                                % ', '.join(missing))
                return False
        return True


    def install(self, packName):
        zp = None
        try:
            zp = self.dmd.ZenPackManager.packs._getOb(packName)
            self.log.info('Upgrading %s' % packName)
            zp.upgrade(self.app)
        except AttributeError:
            try:
                module =  __import__('Products.' + packName, globals(), {}, [''])
                zp = module.ZenPack(packName)
            except (ImportError, AttributeError), ex:
                self.log.debug("Unable to find custom ZenPack (%s), "
                               "defaulting to generic ZenPack",
                               ex)
                zp = ZenPack(packName)
            self.dmd.ZenPackManager.packs._setObject(packName, zp)
            zp = self.dmd.ZenPackManager.packs._getOb(packName)
            zp.install(self.app)
        if zp:
            for required in zp.requires:
                try:
                    self.dmd.ZenPackManager.packs._getOb(required)
                except:
                    self.log.error("Pack %s requires pack %s: not installing",
                                   packName, required)
                    return
        transaction.commit()

    def remove(self, packName):
        self.log.debug('Removing Pack "%s"' % packName)
        for pack in self.dmd.ZenPackManager.packs():
            if packName in pack.requires:
                self.log.error("Pack %s depends on pack %s, not removing",
                               pack.id, packName)
                return
        zp = None
        try:
            zp = self.dmd.ZenPackManager.packs._getOb(packName)
        except AttributeError, ex:
            # Pack not in zeo, might still exist in filesystem
            self.log.debug('No ZenPack named %s in zeo' % packName)
        if zp:
            zp.remove(self.app)
            self.dmd.ZenPackManager.packs._delObject(packName)
        root = zenPath('Products', packName)
        self.log.debug('Removing %s' % root)
        recurse = ""
        if os.path.isdir(root):
            recurse = "r"
        os.system('rm -%sf %s' % (recurse, root))
        cleanupSkins(self.dmd)


    def extract(self, fname):
        "Unpack a ZenPack, and return the name"
        if not os.path.isfile(fname):
            self.stop('Unable to open file "%s"' % fname)
        zf = ZipFile(fname)
        name = zf.namelist()[0]
        packName = name.split('/')[0]
        self.log.debug('Extracting ZenPack "%s"' % packName)
        for name in zf.namelist():
            fullname = zenPath('Products', name)
            self.log.debug('Extracting %s' % name)
            if name.find('/.svn') > -1: continue
            if name.endswith('~'): continue
            if name.endswith('/'):
                if not os.path.exists(fullname):
                    os.makedirs(fullname, 0750)
            else:
                base = os.path.dirname(fullname)
                if not os.path.isdir(base):
                    os.makedirs(base, 0750)
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
        root = zenPath('Products', packName)
        
        # Continue without copying if the srcDir is already in Products
        if os.path.exists(root) and os.path.samefile(root, srcDir):
            self.log.debug('Directory already in %s, not copying.',
                           zenPath('Products'))
            return packName
        
        # Copy the source dir over to Products
        self.log.debug('Copying %s' % packName)
        result = os.system('cp -r %s %s' % (srcDir, zenPath('Products')))
        if result == -1:
            self.stop('Error copying %s to %s' % (srcDir, zenPath('Products')))
        
        return packName


    def linkDir(self, srcDir):
        '''Symlink the srcDir into Products
        Return the name.
        '''
        # Normalize srcDir to not end with slash
        if srcDir.endswith('/'):
            srcDir = srcDir[:-1]
            
        # Need absolute path for links
        srcDir = os.path.abspath(srcDir)
        
        if not os.path.isdir(srcDir):
            self.stop('Specified directory does not appear to exist: %s' %
                        srcDir)
        
        # Determine name of pack and it's destination directory                
        packName = os.path.split(srcDir)[1]
        root = zenPath('Products', packName)
        
        # Continue without copying if the srcDir is already in Products
        if os.path.exists(root) and os.path.samefile(root, srcDir):
            self.log.debug('Directory already in %s, not copying.',
                           zenPath('Products'))
            return packName
      
        targetdir = zenPath("Products", packName)
        cmd = 'test -d %s && rm -rf %s' % (targetdir, targetdir)
        os.system(cmd)
        cmd = 'ln -s %s %s' % (srcDir, zenPath("Products"))
        os.system(cmd)
        
        return packName
        

    def stop(self, why):
        self.log.error("zenpack stopped: %s", why)
        sys.exit(1)
        
    
    def buildOptions(self):
        self.parser.add_option('--install',
                               dest='installPackName',
                               default=None,
                               help="Path to the ZenPack to install.")
        self.parser.add_option('--remove',
                               dest='removePackName',
                               default=None,
                               help="Name of the ZenPack to remove.")
        self.parser.add_option('--list',
                               dest='list',
                               action="store_true",
                               default=False,
                               help='List installed ZenPacks')
        self.parser.add_option('--link',
                               dest='link',
                               action="store_true",
                               default=False,
                               help="Install the ZenPack in place, without "
                                        "copying into $ZENHOME/ZenPacks.")
        self.parser.add_option('--develop',
                               dest='develop',
                               action="store_true",
                               default=False,
                               help="Install the ZenPack in development mode "
                                        "so that it can be edited.")
        self.parser.add_option('--files-only',
                               dest='filesOnly',
                               action="store_true",
                               default=False,
                               help='Install the ZenPack files onto the '
                                        'filesystem, but do not install the '
                                        'ZenPack into Zenoss.')

        ZenScriptBase.buildOptions(self)

if __name__ == '__main__':
    try:
        zp = ZenPackCmd()
        zp.run()
    except ZenPackException, e:
        sys.stderr.write('%s\n' % str(e))
        sys.exit(-1)