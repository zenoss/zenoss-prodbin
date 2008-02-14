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

__doc__="""ZenPackManager
ZenPackManager is a Zope Product that helps manage ZenPacks
"""

from Globals import InitializeClass
from ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *
from AccessControl import ClassSecurityInfo


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
        ('packs', ToManyCont(ToOne, 'Products.ZenModel.ZenPack', 'root')),
        )

    factory_type_information = (
        {
            'immediate_view' : 'viewZenPacks',
            'actions'        :
            (
                { 'name'          : 'ZenPacks'
                , 'action'        : 'viewZenPacks'
                , 'permissions'   : ( 'Manage DMD', )
                },
            )
         },
        )

    security = ClassSecurityInfo()


    def manage_addZenPack(self, packId, package, REQUEST=None):
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
                REQUEST['message'] = msg
                return self.callZenScreen(REQUEST)
            raise ZenPackNeedMigrateException(msg)

        # Make sure a zenpack can be created with given info
        canCreate, msg = ZenPackCmd.CanCreateZenPack(self, packId, package)
        if not canCreate:
            if REQUEST:
                REQUEST['message'] = msg
                return self.callZenScreen(REQUEST, redirect=False)
            raise ZenPackException(msg)
        
        # Create it
        zpDir = ZenPackCmd.CreateZenPack(packId, package)
        
        # Install it
        zenPack = ZenPackCmd.InstallZenPack(self.dmd, zpDir, True)
        
        if REQUEST:
            return REQUEST['RESPONSE'].redirect(zenPack.getPrimaryUrlPath())
        return zenPack


    def manage_removeZenPacks(self, ids=(), REQUEST=None):
        """
        Uninstall the given zenpacks.  Uninstall the zenpack egg.  If not in
        development mode then also delete the egg from the filesystem.
        """
        raise ZenPackException, 'Not implemented'

        # if not getattr(self.dmd, 'ZenPackManager'):
        #     msg = 'Your Zenoss database appears to be out of date. Try ' \
        #             'running zenmigrate to update.'
        #     if REQUEST:
        #         REQUEST['message'] = msg
        #         return self.callZenScreen(REQUEST)
        #     raise ZenPackNeedMigrateException(msg)

        # zp = zenPath('bin', 'zenpack')
        # for pack in ids:
        #     os.system('%s run --remove %s' % (zp, pack))
        # self._p_jar.sync()
        # if REQUEST is not None:
        #     return self.callZenScreen(REQUEST, redirect=True)


    def manage_installZenPack(self, zenpack=None, REQUEST=None):
        """
        Installs the given zenpack.  Zenpack is a file upload from the browser.
        """
        import tempfile
        import fcntl
        import popen2
        import signal
        import time
        import select
        
        ZENPACK_INSTALL_TIMEOUT = 120
        
        if not getattr(self.dmd, 'ZenPackManager'):
            msg = 'Your Zenoss database appears to be out of date. Try ' \
                    'running zenmigrate to update.'
            if REQUEST:
                REQUEST['message'] = msg
                return self.callZenScreen(REQUEST)
            raise ZenPackNeedMigrateException(msg)

        if REQUEST:
            REQUEST['cmd'] = ''
            header, footer = self.commandOutputTemplate().split('OUTPUT_TOKEN')
            REQUEST.RESPONSE.write(str(header))
            out = REQUEST.RESPONSE
        else:
            out = None
        
        tFile = None
        child = None
        try:
            try:
                # Write the zenpack to the filesystem                
                tDir = tempfile.gettempdir()
                tFile = open(os.path.join(tDir, zenpack.filename), 'wb')
                tFile.write(zenpack.read())
                tFile.close()
            
                cmd = 'zenpack --install %s' % tFile.name
                child = popen2.Popen4(cmd)
                flags = fcntl.fcntl(child.fromchild, fcntl.F_GETFL)
                fcntl.fcntl(child.fromchild, fcntl.F_SETFL, flags | os.O_NDELAY)
                endtime = time.time() + ZENPACK_INSTALL_TIMEOUT
                self.write(out, '%s' % cmd)
                self.write(out, '')
                pollPeriod = 1
                firstPass = True
                while time.time() < endtime and (firstPass or child.poll()==-1):
                    firstPass = False
                    r, w, e = select.select([child.fromchild],[],[], pollPeriod)
                    if r:
                        t = child.fromchild.read()
                        #We are sometimes getting to this point without any data
                        # from child.fromchild. I don't think that should happen
                        # but the conditional below seems to be necessary.
                        if t:
                            self.write(out, t)
                if child.poll() == -1:
                    self.write(out,
                               'Command timed out for %s' % cmd +
                               ' (timeout is %s seconds)' %
                               ZENPACK_INSTALL_TIMEOUT)
            except:
                self.write(out, 'Error installing ZenPack.')
                self.write(
                    out, 'type: %s  value: %s' % tuple(sys.exc_info()[:2]))
                self.write(out, '')
        finally:
            if child and child.poll() == -1:
                os.kill(child.pid, signal.SIGKILL)
        
        self.write(out, '')
        self.write(out, 'Done installing ZenPack.')
        if REQUEST:
            REQUEST.RESPONSE.write(footer)


    def getZenPackPaths(self):
        '''
        Return a list of paths to currently installed ZenPacks.  This is used
        to test which classes are provided by these ZenPacks.
        '''
        # return [zp.path()
        # for pack in self.packs():
        pass


    def getBrokenPackName(self, ob):
        ''' Extract the zenpack name from the broken module
        '''
        return ob.__class__.__module__.split('.')[1]



InitializeClass(ZenPackManager)
