###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__ = "Convert old-style zenpacks to zenpack eggs"

import Globals
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.ZenModel.ZenPack import ZenPackException
from Utils import zenPath
import ZenPackCmd
import os, sys
import shutil


class Eggify(ZenScriptBase):
    "Eggify ZenPacks"

    def run(self):
        if not self.options.newid:
            raise ZenPackException('You must specify a new id with the'
                ' --newid option.')
        zpName = self.args[0]
        if not os.path.isdir(zenPath('Products', zpName)):
            raise ZenPackException('Can not locate %s.' % zpName +
                ' This command only operates on installed ZenPacks.')
        (possible, msgOrId) = ZenPackCmd.CanCreateZenPack(
                                                    None, self.options.newid)
        if possible:
            newId = msgOrId
        else:
            raise ZenPackException('Unable to eggify %s: %s' % (
                                                            zpName, msgOrId))                        
        
        self.connect()
        
        # Create new zenpack
        eggDir = ZenPackCmd.CreateZenPack(newId)
        
        # Copy old one into new one
        parts = newId.split('.')
        zpDir = os.path.join(eggDir, *parts)
        os.system('rm -rf %s' % zpDir)
        shutil.copytree(zenPath('Products', zpName), zpDir, symlinks=False)
        
        # Create a skins directory if there isn't one
        skinsDir = os.path.join(zpDir, 'skins', zpName)
        if not os.path.isdir(skinsDir):
            os.makedirs(skinsDir)
        
        # Install it
        ZenPackCmd.InstallEggAndZenPack(self.dmd, eggDir, develop=True)

        # Confirm pack is eggified
        pack = self.dmd.ZenPackManager.packs._getOb(zpName, None)
        success = pack and pack.isEggPack()

        if success:
            print('%s successfully converted to %s.' % (zpName, newId))
            print('The code for %s is located at $ZENHOME/ZenPacks/%s' %
                    (newId, newId))
            print('NOTE: If your ZenPack provides DataSource classes '
                    'or any other python class for objects that are stored '
                    'in the object database then further steps are '
                    'required.  Please see the Zenoss Developer Guide for '
                    'more instructions.')        

    def buildOptions(self):
        self.parser.add_option('--newid',
                               dest='newid',
                               default=None,
                               help='Specify a new name for this ZenPack. '
                                'It must contain at least three package names '
                                'separated by periods, the first one being '
                                '"ZenPacks"')
        ZenScriptBase.buildOptions(self)


if __name__ == '__main__':
    e = Eggify()
    try:
        e.run()
    except ZenPackException, e:
        import sys
        sys.stderr.write('%s\n' % str(e))
        sys.exit(-1)
