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
import transaction

import os, sys

class ZenPackCmd(ZenScriptBase):
    "Manage ZenPacks"

    def run(self):
        "Execute the user's request"
        self.connect()
        if self.options.installPackName:
            self.install(self.extract(self.options.installPackName))

        if self.options.removePackName:
            self.remove(self.options.removePackName)

        if self.options.list:
            for zp in self.dmd.packs():
                print '%s (%s)' % (zp.id, sys.modules[zp.__module__].__file__)
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
                os.rmdir(os.path.join(p, d))
        os.rmdir(root)


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
