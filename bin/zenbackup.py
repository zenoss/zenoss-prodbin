#! /usr/bin/env python 
#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''zenbackup

Creates backup of zope data files, zenoss conf files and the events database.
'''

import Globals
from Products.ZenUtils.CmdBase import CmdBase
import sys
import os
import os.path
import tempfile
from datetime import date


class ZenBackup(CmdBase):

    BACKUP_DIR = 'zenossbackup'
    MAX_UNIQUE_NAME_ATTEMPTS = 1000
    
    def __init__(self, noopts=0):
        self.zenhome = os.getenv('ZENHOME')
        
    def getDefaultBackupFile(self):
        def getName(self, index=0):
            return 'zenbackup_%s_%s.tgz' % (date.today().strftime('%Y%m%d'), 
                                            index)
        backupDir = os.path.join(self.zenhome, 'backups')
        if not os.path.exists(backupDir):
            os.mkdir(backupDir)
        for i in range(self.MAX_UNIQUE_NAME_ATTEMPTS):
            name = os.path.join(backupDir, self.getName(i))
            if not os.path.exists(name):
                break
        else:
            sys.stderr.write('Can not determine a unique file name to us'
                    ' in the backup directory (%s).' % backupDir +
                    ' Use --outfile to specify location for the backup'
                    ' file.\n')
            sys.exit(-1)
        
    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--dbname',
                               dest='dbname',
                               default='events',
                               help='events database name')
        self.parser.add_option('--dbuser',
                               dest='dbuser',
                               default='root',
                               help='mysql username')
        self.parser.add_option('--dbpass',
                               dest='dbpass',
                               default=None,
                               help='mysql password')
        self.parser.add_option('--file',
                               dest="file",
                               default=None,
                               help='File to backup to or restore from')
        self.parser.add_option('--restore',
                               dest="restore",
                               type='int'
                               default=False,
                               action='store_true',
                               help='Restore from a previous backup.')
        self.parser.add_option('--quick',
                               dest="quick",
                               default=False,
                               action='store_true',
                               help='If restoring from backup do not create'
                                    ' a backup of existing data first.')

    def makeBackup(self):
        # Create temp backup dir
        rootTempDir = tempfile.mkdtemp()
        tempDir = os.path.join(rootTempDir, self.BACKUP_DIR)
        os.mkdir(tempDir)
        
        # mysqldump to backup dir
        os.system('mysqldump -u%s -p%s %s > %s' % (
                    self.options.dbuser,
                    (self.options.dbpass or ''),
                    self.options.dbname,
                    os.path.join(tempDir, 'events.sql')))

        # backup zopedb
        repozoDir = os.path.join(tempDir, 'repozo')
        os.mkdir(repozoDir)
        os.system('repozo.py --backup --full '
                    '--repository %s --file %s/var/Data.fs' %
                    (repozoDir, self.zenhome))
        
        # /etc to backup dir (except for sockets)
        etcSrc = os.path.join(self.zenhome, 'etc')
        etcBak = os.path.join(tempDir, 'etc')
        os.mkdir(etcBak)
        files = os.listdir(etcSrc)
        for f in files:
            if not f.endswith('sock'):
                os.system('cp %s %s/' % (os.path.join(etcSrc, f), etcBak))
        
        # /perf to backup dir
        os.system('cp -r %s %s/' % (os.path.join(self.zenhome, 'perf'), tempDir))
                                
        # tar, gzip and send to outfile
        if self.options.file:
            outfile = self.options.file
        else:
            outfile = self.getDeaultBackupFile()
        tempHead, tempTail = os.path.split(tempDir)
        os.system('tar czfC %s %s %s' % (outfile, tempHead, tempTail))
        
        # clean up
        os.system('rm -r %s' % rootTempDir)


    def restore(self):
        #### Are you sure?
        
        #### Make sure zenoss is not running
        
        # Create temp backup dir
        
        
        
        
        rootTempDir = tempfile.mkdtemp()
        os.system('cp %s %s/' % (self.options.restore, rootTempDir))
        os.system('tar xzf %s' % self.options.restore)
        tempDir = os.path.join(rootTempDir, self.BACKUP_DIR)
        
        # mysqldump to backup dir
        os.system('mysqldump -u%s -p%s %s > %s' % (
                    self.options.dbuser,
                    (self.options.dbpass or ''),
                    self.options.dbname,
                    os.path.join(tempDir, 'events.sql')))

        # backup zopedb
        repozoDir = os.path.join(tempDir, 'repozo')
        os.mkdir(repozoDir)
        os.system('repozo.py --backup --full '
                    '--repository %s --file %s/var/Data.fs' %
                    (repozoDir, self.zenhome))
        
        # /etc to backup dir (except for sockets)
        etcSrc = os.path.join(self.zenhome, 'etc')
        etcBak = os.path.join(tempDir, 'etc')
        os.mkdir(etcBak)
        files = os.listdir(etcSrc)
        for f in files:
            if not f.endswith('sock'):
                os.system('cp %s %s/' % (os.path.join(etcSrc, f), etcBak))
        
        # /perf to backup dir
        os.system('cp -r %s %s/' % (os.path.join(self.zenhome, 'perf'), tempDir))
                                
        # tar, gzip and send to stdout or outfile
        if self.options.outfile:
            outfile = self.options.outfile
        else:
            outfile = '-'
        tempHead, tempTail = os.path.split(tempDir)
        os.system('tar czfC %s %s %s' % (outfile, tempHead, tempTail))
        
        # clean up
        os.system('rm -r %s' % rootTempDir)


if __name__ == '__main__':
    zb = ZenBackup()
    if len(sys.argv) < 2:
        # Usage message
        zb.parser.print_help()
    elif zb.options.restore:
        # Restore
        if not zb.options.quick:
            # Backup before the restore
            zb.makeBackup()
            # Should write to log telling where backup is
        zb.restore()
    else:
        zb.makeBackup()
        
        