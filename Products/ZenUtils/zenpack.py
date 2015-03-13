##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


"""Script to manage ZenPacks."""

import os
import sys
import logging
import ConfigParser
import glob
import optparse
import subprocess
import shutil
import tempfile
import re
from toposort import toposort_flatten
from zipfile import ZipFile
from StringIO import StringIO
from pkg_resources import parse_requirements, Distribution, DistributionNotFound, get_distribution, parse_version, iter_entry_points

import Globals
import transaction
from zenoss.protocols.services import ServiceException
from ZODB.POSException import ConflictError

from Products.ZenMessaging.audit import audit
from Products.ZenMessaging.queuemessaging.schema import removeZenPackQueuesExchanges
from Products.ZenModel.ZenPack import (
    ZenPack, ZenPackException,
    ZenPackNotFoundException,
    ZenPackNeedMigrateException
)
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.ZenUtils.Utils import cleanupSkins, zenPath, binPath, get_temp_dir
import Products.ZenModel.ZenPackLoader as ZPL
from Products.ZenModel.ZenPackLoader import CONFIG_FILE, CONFIG_SECTION_ABOUT
import ZenPackCmd as EggPackCmd
from Products.Zuul import getFacade

HIGHER_THAN_CRITICAL = 100
LSB_EXITCODE_PROGRAM_IS_NOT_RUNNING = 3

def RemoveZenPack(dmd, packName, log=None,
                        skipDepsCheck=False, leaveObjects=True,
                        deleteFiles=True):

    if log:
        log.debug('Removing Pack "%s"' % packName)
    if not skipDepsCheck:
        for pack in dmd.ZenPackManager.packs():
            if packName in pack.requires:
                raise ZenPackException('Pack %s depends on pack %s, '
                                        'not removing' % (pack.id, packName))
    zp = None
    try:
        zp = dmd.ZenPackManager.packs._getOb(packName)
    except AttributeError:
        # Pack not in zeo, might still exist in filesystem
        if log:
            log.debug('No ZenPack named %s in zeo' % packName)
    if zp:
        try:
            # In 2.2 we added an additional parameter to the remove method.
            # Any ZenPack subclasses that haven't been updated to take the new
            # parameter will throw a TypeError.
            # The newer version of zenoss-supplied ZenPacks monkey patch
            # older installed versions during an upgrade so that the remove
            # accepts the leaveObjects method.
            zp.remove(dmd, leaveObjects=True)
        except TypeError:
            zp.remove(dmd)
        dmd.ZenPackManager.packs._delObject(packName)
    root = zenPath('Products', packName)
    if deleteFiles:
        if log:
            log.debug('Removing %s' % root)
        recurse = ""
        if os.path.isdir(root):
            recurse = "r"
        os.system('rm -%sf %s' % (recurse, root))
    cleanupSkins(dmd)
    return True


def topo_prioritize(target, graph):
    """
    Add an edge to the target from all other nodes which cannot be reached
    from the target.  This has the effect of moving the node to the front of
    a topological sort.  Edits the graph in place.
    :param target: The node to prioritize
    :param graph: dict node -> list[node], describing the edges of the graph
    :return: none
    """
    # Get all nodes which are reachable from target
    reachableNodes = set()
    stack = [target]
    while stack:
        current = stack.pop(0)
        reachableNodes.add(current)
        stack.extend(graph.get(current, []))
    # Add edge to of all nodes which are not reachable
    for key, val in graph.iteritems():
        if key not in reachableNodes:
            val.add(target)


class ZenPackCmd(ZenScriptBase):
    """Manage ZenPacks"""

    def _verifyZepRunning(self):
        zep = getFacade('zep')
        try:
            zep.getConfig()
            return True
        except ServiceException:
            return False

    def _sameVersion(self):
        """
        Returns True if the zenpack we are trying to install is the same
        version of the zenpack already installed.
        This is mainly used to speed up upgrades, see ticket ZEN-5789
        """
        name, version, unused = self.options.installPackName.split('-', 2)
        # if a path was provided just get the zenpack name
        name = name.split('/')[-1]
        try:
            if self.dmd.ZenPackManager.packs._getOb(name).version == version:
                self.log.info("%s is already at version %s", name, version)
                return True
        except AttributeError:
            # zenpack isn't installed yet
            pass
        return False

    def run(self):
        """Execute the user's request"""
        if self.args:
            print "Require one of --install, --remove, --export, --create, or --list flags."
            self.parser.print_help()
            return

        if self.options.installPackName:
            audit('Shell.ZenPack.Install', zenpack=self.options.installPackName)
        elif self.options.fetch:
            audit('Shell.ZenPack.Fetch', zenpack=self.options.fetch)
        elif self.options.exportPack:
            audit('Shell.ZenPack.Export', zenpack=self.options.exportPack)
        elif self.options.removePackName:
            audit('Shell.ZenPack.Remove', zenpack=self.options.removePackName)
        elif self.options.createPackName:
            audit('Shell.ZenPack.Create', zenpack=self.options.createPackName)


        if self.options.createPackName:
            devDir, packName = os.path.split(self.options.createPackName)
            try:
                self.connect()
                self.dmd.ZenPackManager.manage_addZenPack(packName, devDir=devDir)
            except Exception as ex:
                self.log.fatal("could not create zenpack: %s", ex)
                sys.exit(1)
            sys.exit(0)

        if self.options.installPackName:
            eggInstall = (self.options.installPackName.lower().endswith('.egg')
                or os.path.exists(os.path.join(self.options.installPackName,
                                                'setup.py')))

        if self.options.removePackName and self.options.filesOnly:
            # A files-only remove implies a files-only install.  Egg packs are only supported here.
            installedEggs = [ p for p in iter_entry_points('zenoss.zenpacks') ]
            theOne = filter(lambda x: x.name == self.options.removePackName, installedEggs)
            if not theOne:
                raise ZenPackNotFoundExeption("Specified zenpack not installed")
            if len(theOne) > 1:
                raise ZenPackException("Multipe matching distributions for {} found - aborting.".format(self.options.removePackName))
            actualZPDir = theOne[0].dist.location
            class ZPProxy:
                def __init__(self, zpId, actualPath):
                    self.id = zpId
                    self.actualPath = actualPath
                def path(self, *parts):
                    return self.actualPath
            proxy = ZPProxy(self.options.removePackName, actualZPDir)
            for loader in (ZPL.ZPLDaemons(), ZPL.ZPLBin(), ZPL.ZPLLibExec()):
                loader.unload(proxy, None)
            EggPackCmd.DoEasyUninstall(self.options.removePackName)
            if proxy.path().endswith(".egg") and os.path.exists(proxy.path()):
                self.log.info("Deleting zenpack %s", proxy.path())
                os.system('rm -rf "%s"' % proxy.path())
            else:
                self.log.error("Could not delete %s, skipping", proxy.path())
            return

        self.connect()

        if not getattr(self.dmd, 'ZenPackManager', None):
            raise ZenPackNeedMigrateException('Your Zenoss database appears'
                ' to be out of date. Try running zenmigrate to update.')

        if (self.options.installPackName or self.options.removePackName) and not self._verifyZepRunning():
            print >> sys.stderr, "Error: Required daemon zeneventserver not running."
            print >> sys.stderr, "Execute 'zeneventserver start' and retry the ZenPack installation."
            sys.exit(1)

        if self.options.installPackName:
            if self.options.skipSameVersion and self._sameVersion():
                return
            if not self.preInstallCheck(eggInstall):
                self.stop('%s not installed' % self.options.installPackName)
            if eggInstall:
                return EggPackCmd.InstallEggAndZenPack(
                    self.dmd,
                    self.options.installPackName,
                    link=self.options.link,
                    filesOnly=self.options.filesOnly,
                    previousVersion= self.options.previousVersion,
                    fromUI=self.options.fromui,
                    serviceId=self.options.serviceId)
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

        elif self.options.fetch:
            return EggPackCmd.FetchAndInstallZenPack(self.dmd, self.options.fetch)

        elif self.options.exportPack:
            return EggPackCmd.ExportZenPack(
                self.dmd, self.options.exportPack)
        elif self.options.removePackName:
            pack = self.dmd.ZenPackManager.packs._getOb(
                                        self.options.removePackName, None)

            if not pack:
                if not self.options.ifinstalled:
                    self.log.info('ZenPack %s is not installed.' %
                                            self.options.removePackName)
                    return False
            else:
                if pack:
                    removeZenPackQueuesExchanges(pack.path())
                    if pack.isEggPack():
                        return EggPackCmd.RemoveZenPack(
                                self.dmd, self.options.removePackName)
                RemoveZenPack(self.dmd, self.options.removePackName, self.log)

        elif self.options.list:
            for zpId in self.dmd.ZenPackManager.packs.objectIds():
                try:
                    zp = self.dmd.ZenPackManager.packs._getOb(zpId, None)
                except AttributeError:
                    zp = None
                if not zp:
                    desc = 'broken'
                elif zp.isEggPack():
                    try:
                        desc = zp.eggPath()
                    except DistributionNotFound:
                        desc = "zenpack missing"
                else:
                    desc = zp.path()
                print('%s (%s)' % (zpId,  desc))

        elif self.options.restore:
            self.log.info("Restoring zenpacks")
            self.restore()

        transaction.commit()

    def getPacksPacks(self):
        '''
        Helper method to get a list of the zenpacks in
        /opt/zenoss/packs.  This is representative of what 'shipped' with
        the image being used, and can be used to determine, for example, which
        zenpacks are in the image, but are NOT in the database.
        '''
        packsPath = zenPath('packs')
        if os.path.isdir(packsPath):
            return [ f for f in os.listdir(packsPath) \
                    if os.path.isfile(os.path.join(packsPath, f)) and f.endswith(".egg") ]
        else:
            return []

    def onlyInImage(self):
        '''
        Returns a set of packs to fix (in the image , but not in the database).
        ex. {'ZenPacks.zenoss.ApacheMonitor', 'ZenPacks.zenoss.ZenJMX'}
        '''
        shippedPacks = self.getPacksPacks()
        genericShippedPacks = [ Distribution.from_filename(pack).project_name for pack in shippedPacks ]
        databasePacks = self.dmd.ZenPackManager.packs.objectIds()
        installedPacks = [ p.name for p in iter_entry_points('zenoss.zenpacks') ]
        inPacksNotInDB = set(genericShippedPacks) - set(databasePacks)
        packsToFix = inPacksNotInDB & set(installedPacks)
        return packsToFix

    def restore(self):
        # First take care of packs in the new image that aren't in the database
        fixedSomething = False
        for pack in self.onlyInImage():
             with open(os.devnull, 'w') as fnull:
                 log.info('Erasing zenpack from disk %s', pack)
                 cmd = ['zenpack', '--erase', pack, '--files-only']
                 subprocess.check_call(cmd, stdout=fnull, stderr=fnull)
                 fixedSomething = True

        zpsToRestore = {}
        linkedPacks = []
        for zpId in self.dmd.ZenPackManager.packs.objectIds():
            restoreZenPack = False
            version = None
            filesOnly = True
            try:
                zp = self.dmd.ZenPackManager.packs._objects[zpId]
                # First see if the pack is linked, and add to a separate list
                # if so and move on
                try:
                    if zp.isDevelopment():
                        self.log.info("Found linked zenpack %s", zp)
                        linkedPacks.append(zp)
                        continue
                except (AttributeError, DistributionNotFound):
                    pass
                # If pack is not linked, keep going
                version = getattr(zp, "version", None)
                if version is None:
                    version = zp.__Broken_state__["version"]
                if zp.isEggPack():
                    zp.eggPath() # attempt to raise DistributionNotFound
                versionCmp = cmp(parse_version(get_distribution(zpId).version), parse_version(version))
                if versionCmp != 0:
                    restoreZenPack = True
                    # The distribution package version is higher than what's in zodb
                    if versionCmp > 0:
                        version = get_distribution(zpId).version
                        filesOnly = False
                    # Zodb has a higher version that what's in the distirbution's package
                    elif versionCmp < 0:
                        filesOnly = False

            except (AttributeError, DistributionNotFound):
                restoreZenPack = True
            if version is None:
                self.log.error("Could not determine version of %s, skipping.", zpId)
                continue
            if restoreZenPack:
                # Add to list of packs to restore
                zpsToRestore[zpId] = (version, filesOnly)

        # Restore linekd packs first, separately
        for pack in linkedPacks:
            self._linkedRestore(pack)

        # Figure out which packs have dependencies, and sort them accordingly
        zpsToSort = {}
        pattern = '(ZenPacks\.zenoss\.[a-zA-Z\.]*)'
        for zpId in zpsToRestore.iterkeys():
            zp = self.dmd.ZenPackManager.packs._objects[zpId]
            deps = getattr(zp, 'dependencies', None)
            if deps is None:
                deps = zp.__Broken_state__['dependencies']
            # Look to see if any packs have any other zenpack deps
            matches = filter(
                    lambda x: x,
                    [re.search(pattern, key) for key in deps.keys()]
                )

            depsSet = set()
            # There are ZP deps - get + add them.  If no deps, add empty set
            if len(deps) != 0 and any(matches):
                for match in matches:
                    depName = match.group(0)
                    if depName in zpsToRestore.keys():
                        depsSet.add(depName)
            zpsToSort[zpId] = depsSet

        # If Impact needs upgrading, ensure that it's installed first
        IMPACT = 'ZenPacks.zenoss.Impact'
        if IMPACT in zpsToSort:
            topo_prioritize(IMPACT, zpsToSort)

        def doRestore(pack):
            try:
                self._restore(pack, zpsToRestore[pack][0], zpsToRestore[pack][1])
                return True
            except subprocess.CalledProcessError as cpe:
                self.log.exception(cpe)
                # Keep pack in list of sorted packs, and try again
                # (ZEN-16380).  If B depends on A and A fails, then B will
                # fail too, but that's OK, because it will just try again
                return False

        sortedPacks = toposort_flatten(zpsToSort)
        triedReversing = False
        if len(sortedPacks) > 0:
            fixedSomething = True
        while len(sortedPacks) > 0:
            packListLen = len(sortedPacks)
            # Keep track of all the packs that failed to restore
            self.log.info("Attempting to install packs: %s", ", ".join(sortedPacks))
            sortedPacks[:] = [ pack for pack in sortedPacks if not doRestore(pack) ]
            if len(sortedPacks) == packListLen:
                if triedReversing:
                    self.log.error("Unable to install zenpacks: %s", ", ".join(sortedPacks))
                    sys.exit(1)
                else:
                    # Try reversing the order or packs as a last ditch effort
                    sortedPacks.reverse()
                    triedReversing = True
            elif len(sortedPacks) != 0:
                self.log.info("Failed to install packs: %s, will try again", ", ".join(sortedPacks))

        if not fixedSomething:
            self.log.info("No broken zenpacks found")
        else:
            self.log.info("Successfully restored zenpacks!")

    def _linkedRestore(self, zp):
        """
        Restore a linked zenpack.  The database, easy-install, .pth files, and
        actual linked code should all be intact at this point.
        Parameters:
            zp - ZenPack object to restore (should be linked)
        """
        self.log.info("Restoring linked zenpack %s", zp)
        cmd= ["zenpack", "--link", "--files-only", "--install", zp.eggPath()]
        with open(os.devnull, 'w') as fnull:
            subprocess.check_call(cmd, stdout=fnull, stderr=fnull)

    def _restore(self, zpId, version, filesOnly):
        # glob for backup
        # This is meant to handle standard zenpack naming convention - for exmaple,
        #    ZenPacks.zenoss.OpenStack-1.2.4dev19_5159496-py2.7.egg
        backupDirs = (zenPath(".ZenPacks"), zenPath("packs"))
        dashIndex = version.find('-')
        # If the version has a dash in it, replace it with an underscore
        if dashIndex != -1:
            version = list(version)
            version[dashIndex] = '_'
            version = ''.join(version)
        patterns = [backupDir + "/%s-%s-*" % (zpId, version) for backupDir in backupDirs]
        # Look through potential .egg locations, breaking out once we find one
        # (AKA prefer the first location)
        for pattern in patterns:
            self.log.info("looking for %s", pattern)
            candidates = glob.glob(pattern)
            if len(candidates) > 0:
                break
        if len(candidates) == 0:
            self.log.info("could not find install candidate for %s %s", zpId, version)
            return
        if len(candidates) > 1:
            self.log.error("Found more than one install candidate for %s %s (%s), skipping",
                          zpId, version, ", ".join(candidates))
            return

        # Make the code below this easier to read
        candidate = candidates[0]
        if candidate.lower().endswith(".egg"):
            try:
                shutil.copy(candidate, tempfile.gettempdir())
                cmd = ["zenpack"]
                if filesOnly:
                    cmd.append("--files-only")
                cmd.extend(["--install", os.path.join(tempfile.gettempdir(), os.path.basename(candidate))])
                try:
                    with open(os.devnull, 'w') as fnull:
                        # the first time fixes the easy-install path
                        subprocess.check_call(cmd, stdout=fnull, stderr=fnull)
                except Exception:
                    pass
                # the second time runs the loaders
                subprocess.check_call(cmd)
            finally:
                try:
                    os.remove(os.path.join(tempfile.gettempdir(), os.path.basename(candidate)))
                except Exception:
                    pass
        else:
            self.log.warning("non-egg zenpacks can not currently be restored automatically: %s", candidate)

    def preInstallCheck(self, eggInstall=True):
        """Check that prerequisite zenpacks are installed.
        Return True if no prereqs specified or if they are present.
        False otherwise.
        """
        if eggInstall:
            installedPacks = dict((pack.id, pack.version) \
                             for pack in self.dataroot.ZenPackManager.packs())

            if self.options.installPackName.lower().endswith('.egg'):
                # standard prebuilt egg
                if not os.path.exists(self.options.installPackName):
                    raise ZenPackNotFoundException("Unable to find ZenPack named '%s'" % \
                                           self.options.installPackName)
                zf = ZipFile(self.options.installPackName)
                if 'EGG-INFO/requires.txt' in zf.namelist():
                    reqZenpacks = zf.read('EGG-INFO/requires.txt').split('\n')
                else:
                    return True
            else:
                # source egg, no prebuilt egg-info
                with get_temp_dir() as tempEggDir:
                    cmd = '%s setup.py egg_info -e %s' % \
                                                (binPath('python'), tempEggDir)
                    subprocess.call(cmd, shell=True,
                                    stdout=open('/dev/null', 'w'),
                                    cwd=self.options.installPackName)

                    eggRequires = os.path.join(tempEggDir,
                                    self.options.installPackName + '.egg-info',
                                    'requires.txt')
                    if os.path.isfile(eggRequires):
                        reqZenpacks = open(eggRequires, 'r').read().split('\n')
                    else:
                        return True

            prereqsMet = True
            for req in reqZenpacks:
                if not req.startswith('ZenPacks'):
                    continue
                for parsed_req in parse_requirements([req]):
                    installed_version = installedPacks.get(parsed_req.project_name, None)
                    if installed_version is None:
                        self.log.error('Zenpack %s requires %s' %
                              (self.options.installPackName, parsed_req))
                        prereqsMet = False
                    else:
                        if not installed_version in parsed_req:
                            self.log.error(
                                'Zenpack %s requires %s, found: %s' %
                                (self.options.installPackName, parsed_req, installed_version))
                            prereqsMet = False
            return prereqsMet

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
                    if zp not in self.dataroot.ZenPackManager.packs.objectIds()]
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
            # hide uncatalog error messages since they do not do any harm
            log = logging.getLogger('Zope.ZCatalog')
            oldLevel = log.getEffectiveLevel()
            log.setLevel(HIGHER_THAN_CRITICAL)
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
        finally:
            log.setLevel(oldLevel)
        if zp:
            for required in zp.requires:
                try:
                    self.dmd.ZenPackManager.packs._getOb(required)
                except:
                    self.log.error("Pack %s requires pack %s: not installing",
                                   packName, required)
                    return
        transaction.commit()

    def extract(self, fname):
        """Unpack a ZenPack, and return the name"""
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
        """Copy an unzipped zenpack to the appropriate location.
        Return the name.
        """
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
        """Symlink the srcDir into Products
        Return the name.
        """
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
        self.parser.add_option('--create',
                               dest='createPackName',
                               default=None,
                               help="Zenpack name or path to full destination path, eg /home/zenoss/src/ZenPacks.example.TestPack")
        self.parser.add_option('--install',
                               dest='installPackName',
                               default=None,
                               help="Path to the ZenPack to install.")
        self.parser.add_option('--fetch',
                               dest='fetch',
                               default=None,
                               help="Name of ZenPack to retrieve from Zenoss and install")
        self.parser.add_option('--export',
                               dest='exportPack',
                               default=None,
                               help="Name of the ZenPack to export.")
        self.parser.add_option('--remove', '--delete', '--uninstall', '--erase',
                               dest='removePackName',
                               default=None,
                               help="Name of the ZenPack to remove.")
        self.parser.add_option('--restore',
                               dest='restore',
                               action="store_true",
                               default=False,
                               help='restore missing zenpacks')
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
        self.parser.add_option('--files-only',
                               dest='filesOnly',
                               action="store_true",
                               default=False,
                               help='Install the ZenPack files onto the '
                                        'filesystem, but do not install the '
                                        'ZenPack into Zenoss.')
        self.parser.add_option('--fromui',
                               dest='fromui',
                               action="store_true",
                               default=False,
                               help=optparse.SUPPRESS_HELP)
        self.parser.add_option('--previousversion',
                               dest='previousVersion',
                               default=None,
                               help="Previous version of the zenpack;"
                                    ' used during upgrades')
        self.parser.add_option('--if-installed',
                               action="store_true",
                               dest='ifinstalled',
                               default=False,
                               help="Delete ZenPack only if installed")
        self.parser.add_option('--skip-same-version',
                               action="store_true",
                               dest='skipSameVersion',
                               default=False,
                               help="Do not install the zenpack if the version is unchanged")
        self.parser.add_option('--service-id',
                               dest='serviceId',
                               default=os.getenv('CONTROLPLANE_SERVICED_ID', ''),
                               help=optparse.SUPPRESS_HELP)

        self.parser.prog = "zenpack"
        ZenScriptBase.buildOptions(self)
        self.parser.defaults['logpath'] = zenPath('log')

if __name__ == '__main__':
    logging.basicConfig()
    log = logging.getLogger('zen.ZenPackCmd')
    try:
        zp = ZenPackCmd()
        zp.run()
    except ConflictError:
        sys.exit(LSB_EXITCODE_PROGRAM_IS_NOT_RUNNING)
    except SystemExit as e:
        if e.code:
            sys.exit(LSB_EXITCODE_PROGRAM_IS_NOT_RUNNING)
    except ZenPackNotFoundException as e:
        log.error(e)
        sys.exit(LSB_EXITCODE_PROGRAM_IS_NOT_RUNNING)
    except Exception:
        log.exception('zenpack command failed')
        sys.exit(LSB_EXITCODE_PROGRAM_IS_NOT_RUNNING)
