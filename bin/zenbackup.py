#! /usr/bin/env python 
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
# This program is part of Zenoss Core, an open source monitoring platform.
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
# For complete information please visit: http://www.zenoss.com/oss/
# This program is part of Zenoss Core, an open source monitoring platform.
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
# For complete information please visit: http://www.zenoss.com/oss/
# This program is part of Zenoss Core, an open source monitoring platform.
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
# For complete information please visit: http://www.zenoss.com/oss/

__doc__='''zenbackup

Creates backup of zope data files, zenoss conf files and the events database.
'''

import Globals
from Products.ZenUtils.CmdBase import CmdBase
from Products.ZenUtils.ZCmdBase import ZCmdBase
import sys
import os
import os.path
import tempfile
from datetime import date
import getpass
import ConfigParser
import time
import commands
from zenbackupcommon import *
MAX_UNIQUE_NAME_ATTEMPTS = 1000


class ZenBackup(CmdBase):


    def __init__(self, noopts=0):
        CmdBase.__init__(self, noopts)
        self.zenhome = os.getenv('ZENHOME')
        
    
    def isZeoUp(self):
        ''' Returns True is zeo appears to be running, false otherwise.
        '''
        cmd = '%s/bin/zeoup.py -p 8100' % self.zenhome
        output = commands.getoutput(cmd)
        return output.startswith('Elapsed time:')


    def readSettingsFromZeo(self):
        ''' Return dbname, dbuser, dbpass from saved settings
        '''
        zcmd = ZCmdBase(noopts=True)
        zem = zcmd.dmd.ZenEventManager
        for key, default, zemAttr in CONFIG_FIELDS:
            if not getattr(self.options, key, None):
                setattr(self.options, key, 
                            getattr(zem, zemAttr, None) or default)

            
    def saveSettings(self, tempDir):
        ''' Save some of the options to a file for use during restore
        '''
        config = ConfigParser.SafeConfigParser()
        config.add_section(CONFIG_SECTION)
        config.set(CONFIG_SECTION, 'dbname', self.options.dbname or '')
        config.set(CONFIG_SECTION, 'dbuser', self.options.dbuser or '')
        config.set(CONFIG_SECTION, 'dbpass', self.options.dbpass or '')
        f = open(os.path.join(tempDir, CONFIG_FILE), 'w')
        try:
            config.write(f)
        finally:
            f.close()


    def getDefaultBackupFile(self):
        def getName(index=0):
            return 'zenbackup_%s%s.tgz' % (date.today().strftime('%Y%m%d'), 
                                            (index and '_%s' % index) or '')
        backupDir = os.path.join(self.zenhome, 'backups')
        if not os.path.exists(backupDir):
            os.mkdir(backupDir)
        for i in range(MAX_UNIQUE_NAME_ATTEMPTS):
            name = os.path.join(backupDir, getName(i))
            if not os.path.exists(name):
                break
        else:
            sys.stderr.write('Can not determine a unique file name to us'
                    ' in the backup directory (%s).' % backupDir +
                    ' Use --outfile to specify location for the backup'
                    ' file.\n')
            sys.exit(-1)
        return name


    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        CmdBase.buildOptions(self)
        self.parser.add_option('--dbname',
                               dest='dbname',
                               default=None,
                               help='MySQL events database name.  If'
                                    ' --dont-fetch-args or zenoss is not'
                                    ' available then defaults to "events"')
        self.parser.add_option('--dbuser',
                               dest='dbuser',
                               default=None,
                               help='MySQL username.  If'
                                    ' --dont-fetch-args or zenoss is not'
                                    ' available then defaults to "root"')
        self.parser.add_option('--dbpass',
                               dest='dbpass',
                               default=None,
                               help='MySQL password.')
        self.parser.add_option('--dont-fetch-args',
                                dest='fetchArgs',
                                default=True,
                                action='store_false',
                                help='By default dbname, dbuser and dbpass'
                                    ' are retrieved from zenoss if not'
                                    ' specified and if zenoss is available.'
                                    ' This disables fetching of these values'
                                    ' from zenoss.')
        self.parser.add_option('--file',
                               dest="file",
                               default=None,
                               help='File to backup to.'
                                     ' Backups will by default be placed'
                                     ' in $ZENHOME/backups/')
        self.parser.add_option('--stdout',
                               dest="stdout",
                               default=False,
                               action='store_true',
                               help='Send backup to stdout instead of a file')
        self.parser.add_option('--save-mysql-access',
                                dest='saveSettings',
                                default=False,
                                action='store_true',
                                help='Include dbname, dbuser and dbpass'
                                    ' in backup'
                                    ' file for use during restore.')


    def makeBackup(self):
        ''' Create a backup of the data and configuration for a zenoss install.
        getWhatYouCan == True means to continue without reporting errors even
        if this appears to be an incomplete zenoss install.
        '''        
        # Setup defaults for db info
        if self.options.fetchArgs and self.isZeoUp():
            self.readSettingsFromZeo()
                        
        if self.options.dbname == None:
            self.options.dbname = 'events'
        if self.options.dbuser == None:
            self.options.dbuser = 'zenoss'
        if self.options.dbpass == None:
            self.options.dbpass = 'zenoss'
    
        # Create temp backup dir
        rootTempDir = tempfile.mkdtemp()
        tempDir = os.path.join(rootTempDir, BACKUP_DIR)
        os.mkdir(tempDir)
        
        # Save options to a file for use during restore
        if self.options.saveSettings:
            self.saveSettings(tempDir)
        
        # mysqldump to backup dir
        cmd = 'mysqldump -u%s -p%s --routines %s > %s' % (
                    self.options.dbuser,
                    (self.options.dbpass or ''),
                    self.options.dbname,
                    os.path.join(tempDir, 'events.sql'))
        if os.system(cmd): return -1

        # backup zopedb
        repozoDir = os.path.join(tempDir, 'repozo')
        os.mkdir(repozoDir)
        cmd = ('%s --backup --full ' % 
                os.path.join(self.zenhome, 'bin', 'repozo.py') +
                '--repository %s --file %s/var/Data.fs' %
                (repozoDir, self.zenhome))
        if os.system(cmd): return -1
        
        # /etc to backup dir (except for sockets)
        cmd = 'tar -cf %s --exclude *.zdsock --directory %s %s' % (
                    os.path.join(tempDir, 'etc.tar'),
                    self.zenhome,
                    'etc')        
        if os.system(cmd): return -1

        # /perf to backup dir
        cmd = 'tar Ccf %s %s %s' % (
                    self.zenhome,
                    os.path.join(tempDir, 'perf.tar'),
                    'perf')
        if os.system(cmd): return -1
                                
        # tar, gzip and send to outfile
        if self.options.file:
            outfile = self.options.file
        else:
            outfile = self.getDefaultBackupFile()
        tempHead, tempTail = os.path.split(tempDir)
        if self.options.stdout:
            cmd = 'tar czC %s %s' % (tempHead, tempTail)
        else:
            cmd = 'tar czfC %s %s %s' % (outfile, tempHead, tempTail)

        if os.system(cmd): return -1

        # clean up
        cmd = 'rm -r %s' % rootTempDir
        if os.system(cmd): return -1
        
        return 0


if __name__ == '__main__':
    zb = ZenBackup()
    if (zb.makeBackup()): sys.exit(-1)
