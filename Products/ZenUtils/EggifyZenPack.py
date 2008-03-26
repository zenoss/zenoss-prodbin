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


class Eggify(ZenScriptBase):
    "Eggify ZenPacks"

    def run(self):
        if not self.options.package:
            raise ZenPackException('You must specify a package name with the'
                ' --package option.  This is frequently a company name or'
                ' the zenpack author\'s name.')
        if not self.options.package == ZenPackCmd.ScrubModuleName(
                                                    self.options.package):
            raise ZenPackException('The package name must start with a letter'
                ' and contain only letters, digits and underscores.')
        # if ZenPackCmd.ScrubModuleName(self.options.package).lower() == 'zenoss':
        #     raise ZenPackException('The package name %s is reserved' % 
        #         self.options.package +
        #         ' for use by Zenoss-supplied ZenPacks.  Please use a'
        #         ' different package name.')
        
        dsWarning = []
        for zpName in self.args:
            if not os.path.isdir(zenPath('Products', zpName)):
                raise ZenPackException('Can not locate %s.' % zpName +
                    ' This command only operates on installed ZenPacks.')
            (possible, msg) = ZenPackCmd.CanCreateZenPack(
                                        None, zpName, self.options.package)
            if not possible:
                raise ZenPackException('Unable to eggify %s: %s' % (
                                                                zpName, msg))
            # f = open(zenPath('Products', zpName, '__init__.py'))
            # try:
            #     for line in f:
            #         if line.startswith('class ZenPack'):
            #             raise ZenPackException('Unable to eggify %s' % zpName +
            #                 ' because %s/__init__.py appears to' % zpName +
            #                 ' define a ZenPack subclass.')
            # finally:
            #     f.close()
                        
            dsDir = zenPath('Products', zpName, 'datasources')
            if os.path.isdir(dsDir) and \
                    [f for f in os.listdir(dsDir) if f.endswith('.py')]:
                dsWarning.append(zpName)
                # sys.stderr.write('This ZenPack appears to provide DataSource'
                #     ' classes.  Make sure you have a migrate script to'
                #     ' migrate existing DataSource instances to use the class'
                #     ' from your new ZenPack.  Also make sure your DataSource'
                #     ' class inherits from ZenPackPersistance.\n')
                # raise ZenPackException('Unable to eggify %s' % zpName +
                #     ' because it appears to provide datasource classes.')
        
        self.connect()
        
        success = []
        for zpName in self.args:
            eggDir = ZenPackCmd.CreateZenPack(zpName, self.options.package)
            zpDir = '%s/ZenPacks/%s/%s' % (eggDir, self.options.package, zpName)
            os.system('rm -r %s' % zpDir)
            os.system('cp -r %s %s' % (zenPath('Products', zpName), zpDir))
            ZenPackCmd.InstallEggAndZenPack(self.dmd, eggDir, develop=True)

            # Confirm pack is eggified
            pack = self.dmd.ZenPackManager.packs._getOb(zpName, None)
            if pack and pack.isEggPack():
                success.append(zpName)
            
        print('Eggs have been created for the following ZenPacks.  Their'
            ' source code is located under $ZENHOME/ZenPackDev: '),
        print(','.join(success))
        print('The following ZenPacks appear to contain DataSource classes.'
                ' Make sure you have created migrate scripts to convert'
                ' instances of these classes to use the new, egg-provided'
                ' class: '),
        print(','.join(dsWarning))
        

    def buildOptions(self):
        self.parser.add_option('--package',
                               dest='package',
                               default=None,
                               help='Python package name to use for converted'
                                    'zenpacks.')
        ZenScriptBase.buildOptions(self)


if __name__ == '__main__':
    e = Eggify()
    try:
        e.run()
    except ZenPackException, e:
        import sys
        sys.stderr.write('%s\n' % str(e))
        sys.exit(-1)
