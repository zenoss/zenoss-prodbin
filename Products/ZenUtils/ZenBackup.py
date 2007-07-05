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


__doc__='''zenbackup

Creates backup of zope data files, zenoss conf files and the events database.
'''

import Globals
from ZCmdBase import ZCmdBase
import sys
import os
import os.path
from datetime import date
import getpass
import ConfigParser
import time
import commands
from ZenBackupBase import *

MAX_UNIQUE_NAME_ATTEMPTS = 1000


class ZenBackup(ZenBackupBase):
        
        
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
        config.set(CONFIG_SECTION, 'dbname', self.options.dbname)
        config.set(CONFIG_SECTION, 'dbuser', self.options.dbuser)
        if self.options.dbpass != None:
            config.set(CONFIG_SECTION, 'dbpass', self.options.dbpass)
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
            os.mkdir(backupDir, 0750)
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
        ZenBackupBase.buildOptions(self)
        self.parser.add_option('--dbname',
                               dest='dbname',
                               default=None,
                               help='MySQL events database name.'
                                ' By default this will be fetched from zenoss'
                                ' unless --dont-fetch-args is set.'),
        self.parser.add_option('--dbuser',
                               dest='dbuser',
                               default=None,
                               help='MySQL username.'
                                ' By default this will be fetched from zenoss'
                                ' unless --dont-fetch-args is set.'),
        self.parser.add_option('--dbpass',
                               dest='dbpass',
                               default=None,
                               help='MySQL password.'
                                ' By default this will be fetched from zenoss'
                                ' unless --dont-fetch-args is set.'),
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
        self.parser.add_option('--no-eventsdb',
                               dest="noEventsDb",
                               default=False,
                               action='store_true',
                               help='Do not include the events database'
                                    ' in the backup.')
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
        
        # Output from --verbose would screw up backup being send to
        # stdout because of --stdout
        if self.options.stdout and self.options.verbose:
            sys.stderr.write('You cannot specify both'
                                ' --stdout and --verbose.\n')
            sys.exit(-1)
            
        # Setup defaults for db info
        if self.options.fetchArgs and not self.options.noEventsDb:
            if self.isZeoUp():
                self.msg('Getting mysql dbname, user, password from zeo')
                self.readSettingsFromZeo()
            else:
                self.msg('Unable to get mysql info from zeo.'
                            ' Looks like zeo is not running.')
                        
        if not self.options.dbname:
            self.options.dbname = 'events'
        if not self.options.dbuser:
            self.options.dbuser = 'zenoss'
        # A passwd of '' might be valid.  A passwd of None is interpretted
        # as no password.
    
        # Create temp backup dir
        rootTempDir = self.getTempDir()
        tempDir = os.path.join(rootTempDir, BACKUP_DIR)
        os.mkdir(tempDir, 0750)
        
        # Save options to a file for use during restore
        if self.options.saveSettings:
            self.saveSettings(tempDir)
        
        # mysqldump to backup dir
        if self.options.noEventsDb:
            self.msg('Skipping backup of events database.')
        else:
            self.msg('Backup up events database.')
            cmd = 'mysqldump -u"%s" %s --routines %s > %s' % (
                        self.options.dbuser,
                        self.getPassArg(),
                        self.options.dbname,
                        os.path.join(tempDir, 'events.sql'))
            if os.system(cmd): return -1

        # backup zopedb
        self.msg('Backing up zeo database.')
        repozoDir = os.path.join(tempDir, 'repozo')
        os.mkdir(repozoDir, 0750)
        cmd = ('%s --backup --full ' % 
                self.getRepozoPath() +
                '--repository %s --file %s/var/Data.fs' %
                (repozoDir, self.zenhome))
        if os.system(cmd): return -1
        
        # /etc to backup dir (except for sockets)
        self.msg('Backing up config files.')
        cmd = 'tar -cf %s --exclude *.zdsock --directory %s %s' % (
                    os.path.join(tempDir, 'etc.tar'),
                    self.zenhome,
                    'etc')        
        if os.system(cmd): return -1

        # /perf to backup dir
        self.msg('Backing up performance data.')
        cmd = 'tar Ccf %s %s %s' % (
                    self.zenhome,
                    os.path.join(tempDir, 'perf.tar'),
                    'perf')
        if os.system(cmd): return -1
                                
        # tar, gzip and send to outfile
        self.msg('Packaging backup file.')
        if self.options.file:
            outfile = self.options.file
        else:
            outfile = self.getDefaultBackupFile()
        tempHead, tempTail = os.path.split(tempDir)
        cmd = 'tar czfC %s %s %s' % (
                self.options.stdout and '-' or outfile, 
                tempHead, tempTail)
        self.msg('Backup file written to %s' % outfile)

        if os.system(cmd): return -1

        # clean up
        self.msg('Cleaning up temporary files.')
        cmd = 'rm -r %s' % rootTempDir
        if os.system(cmd): return -1
        
        self.msg('Backup complete.')
        return 0


if __name__ == '__main__':
    zb = ZenBackup()
    if zb.makeBackup():
        sys.exit(-1)
