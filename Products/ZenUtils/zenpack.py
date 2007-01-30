"Manage ZenPacks"

import Globals
from Products.ZenModel.ZenPack import ZenPackBase, zenPackPath
from Products.ZenUtils.ZCmdBase import ZCmdBase
import transaction

import os, sys

class ZenPackCmd(ZCmdBase):
    "Manage ZenPacks"

    def run(self):
        "Execute the user's request"
        if self.options.installPackName:
            self.install(self.extract(self.options.installPackName))

        if self.options.removePackName:
            self.remove(self.options.removePackName)

        if self.options.list:
            for zp in self.dmd.packs():
                print '%s (%s)' % (zp.id, sys.modules[zp.__module__].__file__)
            
        transaction.commit()


    def install(self, packName):
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
        zp.install(self)


    def remove(self, packName):
        self.log.debug('Removing Pack "%s"' % packName)
        zp = None
        try:
            zp = self.dmd.packs._getOb(packName)
        except AttributeError, ex:
            self.stop('There is no ZenPack named "%s"' % packName)
        zp.remove(self)
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
        if os.path.isdir(root):
            self.stop("%s already exists" % root)
        self.log.debug('Extracting ZenPack "%s"' % packName)
        for name in zf.namelist():
            self.log.debug('Extracting %s' % name)
            if name.endswith('/'):
                os.makedirs(name)
            else:
                file(name, 'wb').write(zf.read(name))
        return packName
        

    def stop(self, *args):
        self.log.error(*args)
        import sys
        sys.exit(1)
        
    
    def buildOptions(self):
        ZCmdBase.buildOptions(self)
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

if __name__ == '__main__':
    zp = ZenPackCmd()
    zp.run()
