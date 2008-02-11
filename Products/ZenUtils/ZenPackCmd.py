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
__doc__ = "Manage ZenPacks"

import Globals
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.ZenUtils.Utils import cleanupSkins, zenPath
from Products.ZenModel.ZenPack import ZenPackException, ZenPackNotFoundException
from Products.ZenModel.ZenPack import ZenPackDependentsException
from Products.ZenModel.ZenPack import ZenPack
import Products.ZenModel.ZenPackLoader as ZPL
import transaction
import os, sys
import pkg_resources
import shutil
import string
#import zenpacksupport

zpToEggDataMap = {
    'author': 'author',
    'organization': 'organization',
    'description': 'description',
    'authorEmail': 'author_email',
    'maintainer': 'maintainer',
    'maintainerEmail': 'maintainer_email',
    'url': 'url',
    }

def ScrubModuleName(name):
    """
    Return a version of str that is appropriate for a python module name.
    Specifically, it starts with a letter and is comprised only of digits,
    letters and underscores.
    """
    if not name:
        raise ZenPackException('Module name must not be empty.')
    allowable = string.letters + string.digits + '_'
    safe = ''
    for c in name:
        if c in allowable:
            safe += c
        else:
            safe += '_'
    if safe[0] not in string.letters + '_':
        safe = '_' + safe
    return safe


def CanCreateZenPack(dmd, zpId, package):
    """
    Return tuple (bool, string) where first element is true if a new zenpack
    can be created with the given info and false if not.  The string is empty
    in the first case and contains an explanatory message in the second.
    """
    # Check if id and package looks reasonable
    if zpId != ScrubModuleName(zpId):
        return (False, 'ZenPack names must start with a letter and contain'
                        ' only letters, digits and underscores.')
    if package != ScrubModuleName(package):
        return (False, 'Package must start with a letter and contain'
                        ' only letters, digits and underscores.')

    # Is the id already in use?
    if dmd:
        if zpId in dmd.packs.objectIds():
            return (False, 'A ZenPack named %s already exists.' % zpId)

    # Is there an (uninstalled) zenpack in the way?
    if os.path.exists(zenPath('ZenPackDev', zpId)):
        return (False, 'A directory named %s already exists' % zpId +
                        ' in $ZENHOME/ZenPackDev.  Use a different name'
                        ' or remove that directory.')

    return (True, '')


def CreateZenPack(zpId, package):
    """
    Create the zenpack in the filesystem.
    The zenpack is not installed in Zenoss, it is simply created in
    the $ZENHOME/ZenPacks directory.  Usually this should be followed
    with a "zenpack install" call.
    zpId should already be valid, scrubbed value.
    organization will be scrubbed for use in namespace package.
    """
    
    # Copy template to $ZENHOME/ZenPackDev
    srcDir = zenPath('Products', 'ZenModel', 'ZenPackTemplate')
    devDir = zenPath('ZenPackDev')
    if not os.path.exists(devDir):
        os.mkdir(devDir, 0750)
    destDir = os.path.join(devDir, zpId)
    shutil.copytree(srcDir, destDir, symlinks=False)
    os.system('find %s -name .svn | xargs rm -rf' % destDir)
    
    mapping = {
        'ZENPACKID': zpId,
        'PACKAGE': package,
        }

    # Write zenpackid and package to the setup file.
    setupPath = os.path.join(destDir, 'setup.py')
    f = open(setupPath, 'r')
    setup = f.read()
    f.close()
    for k, v in mapping.items():
        setup = setup.replace(k, v)
    f = open(setupPath, 'w')
    f.write(setup)
    f.close()
    
    # Rename directories         
    for dirPath, dirNames, fileNames in os.walk(destDir, topdown=False):
        for dirName in dirNames:
            if dirName in mapping.keys():
                os.rename(os.path.join(dirPath, dirName),
                            os.path.join(dirPath, mapping[dirName]))

    return destDir


def ReadZenPackInfo(dist):
    """
    Return a dictionary containing the egg metadata
    """
    info = {}
    if dist.has_metadata('PKG-INFO'):
        lines = dist.get_metadata('PKG-INFO')
        for line in pkg_resources.yield_lines(lines):
            key, value = line.split(':', 1)
            info[key.strip()] = value.strip()
    return info


def CopyMetaDataToZenPackObject(dist, pack):
    """
    Copy metadata type stuff from the distribution to the zp object.
    """
    # Version
    pack.version = dist.version
    # Egg Info
    info = ReadZenPackInfo(dist)
    pack.author = info.get('author', '')
    # pack.organization = info.get('organization', '')
    # pack.description = info.get('description', '')
    # pack.authorEmail = info.get('author_email', '')
    # pack.maintainer = info.get('maintainer', '')
    # pack.maintainerEmail = info.get('maintainerEmail', '')


def InstallZenPack(dmd, eggPath, develop=False, filesOnly=False):
    """
    Installs the given egg, instantiates the ZenPack, installs in
    dmd.packs, and runs the zenpacks's install method.
    """
    import pkg_resources

    # Make sure $ZENHOME/ZenPacks exists
    zpDir = zenPath('ZenPacks')
    if not os.path.isdir(zpDir):
        os.mkdir(zpDir, 0750)

    eggPath = os.path.abspath(eggPath)

    # Install the egg
    zenPackDir = zenPath('ZenPacks')
    if develop:
        os.chdir(eggPath)
        r = os.system('python setup.py develop '
                        '--site-dirs=%s ' % zenPackDir +
                        '-d %s' % zenPackDir)
    else:
        r = os.system('easy_install --always-unzip --site-dirs=%s -d %s %s' % (
                    zenPackDir,
                    zenPackDir,
                    eggPath))
        eggName = os.path.split(eggPath)[1]
        eggPath = os.path.join(zenPackDir, eggName)

    # Add egg to working_set
    distGen = pkg_resources.find_distributions(eggPath)
    dist = distGen.next()
    pkg_resources.working_set.add(dist)
    pkg_resources.require(dist.project_name)

    # Instantiate ZenPack
    entryMap = pkg_resources.get_entry_map(dist, 'zenoss.zenpacks')
    if not entryMap or len(entryMap) > 1:
        raise ZenPackException, 'A ZenPack egg must contain exactly one' \
                ' zenoss.zenpacks entry point.  This egg appears to contain' \
                ' %s such entry points.' % len(entryMap)
    packName, packEntry = entryMap.items()[0]
    module = packEntry.load()
    if hasattr(module, 'ZenPack'):
        zenPack = module.ZenPack(packName)
    else:
        zenPack = ZenPack(packName)
    zenPack.eggPack = True
    if develop:
        zenPack.development = True
    CopyMetaDataToZenPackObject(dist, zenPack)


    if filesOnly:
        for loader in (ZPL.ZPLDaemons(), ZPL.ZPLBin(), ZPL.ZPLLibExec()):
            loader.load(zenPack, None)
    else:
        # If upgrading from non-egg to egg this is probably where the 
        # object conversion needs to take place.
        existing = dmd.packs._getOb(packName, None)
        if existing:
            if existing.isEggPack():
                zenPack.upgrade(dmd)
            elif zenPack.__class__ == existing.__class__:
                # This does not yet handle changing classes of custom
                # datasources, etc.
                existing.eggPack = True
                existing.development = zenPack.development
                zenPack = existing
                zenPack.upgrade(dmd)
            else:
                raise ZenPackException('Upgrading ZenPacks with custom'
                    ' classes is not supported yet.')
        else:
            dmd.packs._setObject(packName, zenPack)
            zenPack = dmd.packs._getOb(packName)    
            zenPack.install(dmd)
        transaction.commit()
    
    return zenPack


def CanRemoveZenPack(dmd, packName):
    """
    Return True if this ZenPack can be removed, False otherwise.
    A ZenPack can be removed if no other installed ZenPack list it as
    as dependency.
    """
    if GetDependents(dmd, packName):
        return False
    return True


def GetDependents(dmd, packName):
    """
    Return a list of installed ZenPack ids that list packName as a dependency
    """
    return [zp.id for zp in dmd.packs() 
                if zp.id != packName and zp.dependencies.has_key(packName)]


def CleanupEasyInstallPth(eggLink):
    # Remove the path from easy-install.pth
    easyPth = zenPath('ZenPacks', 'easy-install.pth')
    f = open(easyPth, 'r')
    newLines = [l for l in f if l.strip() != eggLink]
    f.close()
    f = open(easyPth, 'w')
    f.writelines(newLines)
    f.close()


def RemoveZenPack(dmd, packName, filesOnly=False):
        
    # Check for dependency implications here?
    
    if not filesOnly:
        deps = GetDependents(dmd, packName)
        if deps:
            raise ZenPackDependentsException('%s cannot be removed ' % packName +
                    'because it is required by %s' % ', '.join(deps))

        # Fetch the zenpack, call its remove() and remove from dmd.packs
        zp = None
        try:
            zp = dmd.packs._getOb(packName)
        except AttributeError, ex:
            raise ZenPackNotFoundException('No ZenPack named %s is installed' % 
                                            packName)
        zp.remove(dmd)
        dmd.packs._delObject(packName)
    
    # Uninstall the egg and possibly delete it
    # If we can't find the distribution then apparently the zp egg itself is 
    # missing.  Continue on with the removal and swallow the 
    # DistributionNotFound exception
    try:
        dist = zp.getDistribution()
    except pkg_resources.DistributionNotFound:
        dist = None
    if dist:
        if zp.isDevelopment():
            # Leave development mode zenpacks in place.  The user has to
            # delete development mode code themselves.
            # Remove the egg-link from $ZENHOME/ZenPacks
            link = zenPath('ZenPacks', '%s.egg-link' % zp.id)
            if os.path.isfile(link):
                os.remove(link)
            eggLink = zp.eggPath()
        else:        
            # This has the unfortunate side effect of actually installing
            # dependencies it seems.
            # r = os.system('easy_install --site-dirs=%s -m %s' % (
            #                     zenPath('ZenPacks'), zp.id))
            r = os.system('rm -rf %s' % zp.eggPath())
            eggLink = './%s' % zp.eggName()

    CleanupEasyInstallPth(eggLink)
    cleanupSkins(dmd)
    
    transaction.commit()


class ZenPackCmd(ZenScriptBase):
    "Manage ZenPacks"

    def run(self):
        "Execute the user's request"
        self.connect()
        if self.options.eggPath:
            return InstallZenPack(self.dmd, self.options.eggPath, False,
                                    self.options.filesOnly)
        elif self.options.developPath:
            return InstallZenPack(self.dmd, self.options.developPath, True,
                                    self.options.filesOnly)
        elif self.options.removePackName:
            try:
                return RemoveZenPack(self.dmd, self.options.removePackName)
            except ZenPackNotFoundException, e:
                sys.stderr.write(str(e) + '\n')
        elif self.options.list:
            self.list()


    def buildOptions(self):
        self.parser.add_option('--install',
                               dest='eggPath',
                               default=None,
                               help="name of the pack to install")
        self.parser.add_option('--develop',
                               dest='developPath',
                               default=None,
                               help='name of the pack to install in '
                                    'development mode')
        self.parser.add_option('--remove',
                               dest='removePackName',
                               default=None,
                               help="name of the pack to remove")
        self.parser.add_option('--files-only',
                               dest='filesOnly',
                               action="store_true",
                               default=False,
                               help='install onto filesystem but not into '
                                        'zenoss')
        ZenScriptBase.buildOptions(self)


if __name__ == '__main__':
    try:
        zp = ZenPackCmd()
        zp.run()
    except ZenPackException, e:
        sys.stderr.write('%s\n' % str(e))
        sys.exit(-1)
