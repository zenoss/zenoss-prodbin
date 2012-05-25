###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__="""ZenPackManager
ZenPackManager is a Zope Product that helps manage ZenPacks
"""

from Globals import InitializeClass
from ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *
from AccessControl import ClassSecurityInfo
from ZenossSecurity import ZEN_MANAGE_DMD
from Products.ZenMessaging.audit import audit
from Products.ZenUtils.Utils import binPath
from Products.ZenWidgets import messaging
import os

def manage_addZenPackManager(context, newId='', REQUEST=None):
    """
    Create a ZenPackManager instance
    """
    if not newId:
        newId = 'ZenPackManager'
    zpm = ZenPackManager(newId)
    context._setObject(newId, zpm)
    zpm = context._getOb(newId)
    if REQUEST is not None:
        REQUEST.RESPONSE.redirect(context.absolute_url() + '/manage_main') 


class ZenPackManager(ZenModelRM):
    """
    ZenPackManager is responsibe for managing ZenPacks
    """

    portal_type = meta_type = 'ZenPackManager'

    default_catalog = 'zenPackNameSearch'

    _relations = ZenModelRM._relations + (
        ('packs', ToManyCont(ToOne, 'Products.ZenModel.ZenPack', 'manager')),
        )

    factory_type_information = (
        {
            'immediate_view' : 'viewZenPacks',
            'actions'        :
            (
                { 'id'            : 'settings'
                , 'name'          : 'Settings'
                , 'action'        : '../editSettings'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Commands'
                , 'action'        : '../dataRootManage'
                , 'permissions'   : ('Manage DMD',)
                },
                { 'id'            : 'users'
                , 'name'          : 'Users'
                , 'action'        : '../ZenUsers/manageUserFolder'
                , 'permissions'   : ( 'Manage DMD', )
                },
                { 'id'            : 'packs'
                , 'name'          : 'ZenPacks'
                , 'action'        : 'viewZenPacks'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'portlets'
                , 'name'          : 'Portlets'
                , 'action'        : '../editPortletPerms'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'daemons'
                , 'name'          : 'Daemons'
                , 'action'        : '../About/zenossInfo'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'versions'
                , 'name'          : 'Versions'
                , 'action'        : '../About/zenossVersions'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'backups'
                , 'name'          : 'Backups'
                , 'action'        : '../backupInfo'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'eventConfig'
                , 'name'          : 'Events'
                , 'action'        : 'eventConfig'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'userInterfaceConfig'
                , 'name'          : 'User Interface'
                , 'action'        : '../userInterfaceConfig'
                , 'permissions'   : ( "Manage DMD", )
                },
            )
         },
        )

    security = ClassSecurityInfo()


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_addZenPack')
    def manage_addZenPack(self, packId, REQUEST=None):
        """
        Create a new zenpack on the filesystem with the given info.
        Install the pack.  If REQUEST then render the REQUEST otherwise
        return the new zenpack.
        """
        import Products.ZenUtils.ZenPackCmd as ZenPackCmd 
        
        if not getattr(self.dmd, 'ZenPackManager'):
            msg = 'Your Zenoss database appears to be out of date. Try ' \
                    'running zenmigrate to update.'
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error', msg, priority=messaging.WARNING)
                return self.callZenScreen(REQUEST)
            from ZenPack import ZenPackNeedMigrateException
            raise ZenPackNeedMigrateException(msg)

        # Make sure a zenpack can be created with given info
        canCreate, msgOrId = ZenPackCmd.CanCreateZenPack(self, packId)
        if canCreate:
            packId = msgOrId
        else:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Add ZenPack', msgOrId)
                return self.callZenScreen(REQUEST, redirect=False)
            from ZenPack import ZenPackException
            raise ZenPackException(msgOrId)

        # Create it
        zpDir = ZenPackCmd.CreateZenPack(packId)

        # Install it
        zenPacks = ZenPackCmd.InstallEggAndZenPack(self.dmd, zpDir, link=True,
                                                   forceRunExternal=True)
        zenPack = self.packs._getOb(packId, None)
        audit('UI.ZenPack.Create', packId)
        if REQUEST:
            if zenPack:
                return REQUEST['RESPONSE'].redirect(zenPack.getPrimaryUrlPath())
            messaging.IMessageSender(self).sendToBrowser(
                'Error', 'There was an error creating the ZenPack.',
                priority=messaging.WARNING)
            return self.callZenScreen(REQUEST)
        return zenPack


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_removeZenPacks')
    def manage_removeZenPacks(self, ids=(), REQUEST=None):
        """
        Uninstall the given zenpacks.  Uninstall the zenpack egg.  If not in
        development mode then also delete the egg from the filesystem.
        """
        import Products.ZenUtils.ZenPackCmd as ZenPackCmd 

        if not getattr(self.dmd, 'ZenPackManager'):
            msg = 'Your Zenoss database appears to be out of date. Try ' \
                    'running zenmigrate to update.'
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error', msg, priority=messaging.WARNING)
                return self.callZenScreen(REQUEST)
            from ZenPack import ZenPackNeedMigrateException
            raise ZenPackNeedMigrateException(msg)
        
        canRemove, dependents = ZenPackCmd.CanRemoveZenPacks(self.dmd, ids)
        if not canRemove:
            msg = 'The following ZenPacks depend on one or more of the ' + \
                ' ZenPacks you are trying to remove: %s' % ','.join(dependents)
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error', msg, priority=messaging.WARNING)
                return self.callZenScreen(REQUEST)
            from ZenPack import ZenPackDependentsException
            raise ZenPackDependentsException(msg)
        for zpId in ids:
            zp = self.packs._getOb(zpId, None)
            if zp:
                if zp.isEggPack():
                    ZenPackCmd.RemoveZenPack(self.dmd, zpId, skipDepsCheck=True)
                    audit('UI.ZenPack.Remove', zpId)
                else:
                    os.system('%s --remove %s' % (
                                            binPath('zenpack'), zpId))
                    self._p_jar.sync()
        if REQUEST:
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_MANAGE_DMD, 'fetchZenPack')
    def fetchZenPack(self, packName, packVersion=''):
        """
        Retrieve the given zenpack from Zenoss.net and install.
        """
        import Products.ZenUtils.ZenPackCmd as ZenPackCmd
        zp = ZenPackCmd.FetchAndInstallZenPack(self.dmd, packName, packVersion)
        if REQUEST:
            return REQUEST['RESPONSE'].redirect(zp.getPrimaryUrlPath())
        return zp



    security.declareProtected(ZEN_MANAGE_DMD, 'manage_installZenPack')
    def manage_installZenPack(self, zenpack=None, REQUEST=None):
        """
        Installs the given zenpack.  Zenpack is a file upload from the browser.
        """
        import os
        import re
        from subprocess import Popen, PIPE, STDOUT
        import time

        from Products.ZenUtils.Utils import get_temp_dir

        ZENPACK_INSTALL_TIMEOUT = 10 * 60 # 10 minutes

        if not getattr(self.dmd, 'ZenPackManager'):
            msg = 'Your Zenoss database appears to be out of date. Try ' \
                    'running zenmigrate to update.'
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error', msg, priority=messaging.WARNING)
                return self.callZenScreen(REQUEST)
            from ZenPack import ZenPackNeedMigrateException
            raise ZenPackNeedMigrateException(msg)

        msg = ''
        with get_temp_dir() as tempDir:
            # zenpack.filename gives us filename of the zenpack with the
            # path as it exists on the client. We need just the filename.
            base_filename = re.split(r"\\|/", zenpack.filename)[-1]
            # Macs (and other broswers/OSs) always append a .zip to files they
            # believe to be zip files. Remedy that:
            if base_filename.endswith('.egg.zip'):
                base_filename = base_filename[:-7] + 'egg'

            # Write the zenpack to the filesystem
            tFile = open(os.path.join(tempDir, base_filename), 'wb')
            tFile.write(zenpack.read())
            tFile.close()
            
            p = None # zenpack install process
            try:
                # Run zenpack install
                cmd = 'zenpack --install %s' % tFile.name
                p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)
                endWait = time.time() + ZENPACK_INSTALL_TIMEOUT
                # Wait for install to complete or fail
                while p.poll() is None and time.time() < endWait:
                    time.sleep(1)
                if p.poll() is not None:
                    msg = p.stdout.read()
            finally:
                if p and p.poll() is None:
                    p.kill()
                    msg += 'Zenpack install killed due to timeout'

        if REQUEST:
            # format command result for HTML
            msg = '<br>'.join(line.strip() for line in msg.split('\n') if line.strip())
            messaging.IMessageSender(self).sendToBrowser('Zenpack', msg,
                priority = messaging.CRITICAL if 'ERROR' in msg
                                              else messaging.INFO)
            return self.callZenScreen(REQUEST)
        

    def getZnetProjectOptions(self):
        """
        Return a list of 2-tuples of (option value, option name) for the
        user to select a Zenoss.net project from.
        """
        projects = self.getZnetProjectsList()
        return [(p, p.split('/')[-1]) for p in projects]


    def getZnetProjectsList(self):
        """
        Return a list of the zenoss.net projects.
        """
        import json
        import Products.ZenUtils.DotNetCommunication as DotNetCommunication
        userSettings = self.dmd.ZenUsers.getUserSettings()
        session = DotNetCommunication.getDotNetSession(
                    userSettings.zenossNetUser,
                    userSettings.zenossNetPassword)
        projects = session.retrieve('projectList')
        projects = json.loads(projects)
        return projects


    def getBrokenPackName(self, ob):
        ''' Extract the zenpack name from the broken module
        '''
        return ob.id if ob.id and ob.id != 'broken' else ob.__class__.__module__


InitializeClass(ZenPackManager)
