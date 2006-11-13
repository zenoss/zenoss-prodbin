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


    BACKUP_DIR = 'zenbackup'
    MAX_UNIQUE_NAME_ATTEMPTS = 1000


    def __init__(self, noopts=0):
        CmdBase.__init__(self, noopts)
        self.zenhome = os.getenv('ZENHOME')


    def getDefaultBackupFile(self):
        def getName(index=0):
            return 'zenbackup_%s%s.tgz' % (date.today().strftime('%Y%m%d'), 
                                            (index and '_%s' % index) or '')
        backupDir = os.path.join(self.zenhome, 'backups')
        if not os.path.exists(backupDir):
            os.mkdir(backupDir)
        for i in range(self.MAX_UNIQUE_NAME_ATTEMPTS):
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
        cmd = 'mysqldump -u%s -p%s %s > %s' % (
                    self.options.dbuser,
                    (self.options.dbpass or ''),
                    self.options.dbname,
                    os.path.join(tempDir, 'events.sql'))
        if os.system(cmd): return -1
                    
        # save db name to a file
        cmd = 'echo "%s" > %s' % (self.options.dbname, 
                                os.path.join(tempDir, 'dbname.txt'))
        if os.system(cmd): return -1                                

        # backup zopedb
        repozoDir = os.path.join(tempDir, 'repozo')
        os.mkdir(repozoDir)
        cmd = ('repozo.py --backup --full '
                '--repository %s --file %s/var/Data.fs' %
                (repozoDir, self.zenhome))
        if os.system(cmd): return -1
        
        # /etc to backup dir (except for sockets)
        etcSrc = os.path.join(self.zenhome, 'etc')
        etcBak = os.path.join(tempDir, 'etc')
        os.mkdir(etcBak)
        files = os.listdir(etcSrc)
        for f in files:
            if not f.endswith('sock'):
                cmd = 'cp %s %s/' % (os.path.join(etcSrc, f), etcBak)
                if os.system(cmd): return -1

        # /perf to backup dir
        cmd = 'cp -r %s %s/' % (os.path.join(self.zenhome, 'perf'), tempDir)
        if os.system(cmd): return -1
                                
        # tar, gzip and send to outfile
        if self.options.file:
            outfile = self.options.file
        else:
            outfile = self.getDefaultBackupFile()
        tempHead, tempTail = os.path.split(tempDir)
        cmd = 'tar czfC %s %s %s' % (outfile, tempHead, tempTail)
        if os.system(cmd): return -1

        # clean up
        cmd = 'rm -r %s' % rootTempDir
        if os.system(cmd): return -1
        
        return 0


    def restore(self):
    
        # Are you sure?
        confirm = raw_input('Are you sure you want to restore from backup?'
                '  This will overwrite existing data.  Type YES to proceed.')
        if confirm != 'YES':
            return -1
        
        # Make sure zenoss is not running
        raw_input('Make sure zenoss is not running and press Return.')
        
        # Create temp dir and untar backup into it
        rootTempDir = tempfile.mkdtemp()
        cmd = 'tar xzfC %s %s' % (self.options.file, rootTempDir)
        if os.system(cmd): return -1
        tempDir = os.path.join(rootTempDir, self.BACKUP_DIR)
        
        # Restore mysql
        # Could read dbname from dbname.txt in backup dir if needed maybe
        cmd='mysql -u%s -p%s %s < %s' % (
                            self.options.dbuser,
                            (self.options.dbpass or ''),
                            self.options.dbname,
                            os.path.join(tempDir, 'events.sql'))
        if os.system(cmd): return -1
        
        # Copy etc files
        cmd = 'cp %s %s' % (os.path.join(tempDir, 'etc', '*'),
                            os.path.join(self.zenhome, 'etc'))
        if os.system(cmd): return -1
        
        # Copy perf files
        cmd = 'cp %s %s' % (os.path.join(tempDir, 'perf', '*'),
                            os.path.join(self.zenhome, 'perf'))
        if os.system(cmd): return -1
        
        # restore zopedb
        repozoDir = os.path.join(tempDir, 'repozo')
        cmd ='repozo.py --recover --repository %s --output %s' % (
                    repozoDir,
                    os.path.join(self.zenhome, 'var', 'Data.fs'))
        if os.system(cmd): return -1

        # clean up
        cmd = 'rm -r %s' % rootTempDir
        if os.system(cmd): return -1
        
        return 0


if __name__ == '__main__':

    ##########
    # UNDER DEVELOPMENT - USE AT YOUR OWN RISK
    print ('zenbackup.py is still underdevelopment and almost certainly ' 
            'contains bugs.  If you still wish to use it you can remove ' 
            'these lines from zenbackup.py to enable use.')
    sys.exit(-1)
    ###########

    zb = ZenBackup()

    showUsage = False
    
    required = ['dbname', 'dbuser']
    if zb.options.restore:
        required.append('file')
    for attr in required:
        if not getattr(zb.options, attr, None):
            print 'You must provide a value for %s' % attr
            showUsage = True
            
    if showUsage:
        zb.parser.print_help()

    elif zb.options.restore:
        # Restore
        if zb.options.quick:
            doRestore = True
        else:
            doRestore = not zb.makeBackup()
        if doRestore:
            zb.restore()
    else:
        zb.makeBackup()
        
        