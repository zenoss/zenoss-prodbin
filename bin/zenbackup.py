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
import getpass

# This is written in Python because in was originally a subclass of ZCmdBase.
# Since that is no longer the case this would probably be cleaner now if done
# as a shell script.

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
                               help='MySQL events database name')
        self.parser.add_option('--dbuser',
                               dest='dbuser',
                               default='root',
                               help='MySQL username')
        self.parser.add_option('--dbpass',
                               dest='dbpass',
                               default=None,
                               help='MySQL password (if not specified then'
                                    ' you may be prompted'
                                    ' during the backup/restore')
        self.parser.add_option('--file',
                               dest="file",
                               default=None,
                               help='File to backup to or restore from.'
                                     ' Backups will by default be placed'
                                     ' in %ZENHOME/backups/')
        self.parser.add_option('--restore',
                               dest="restore",
                               default=False,
                               action='store_true',
                               help='Restore from a previous backup.')
        self.parser.add_option('--quick',
                               dest="quick",
                               default=False,
                               action='store_true',
                               help='A backup is by default performed before'
                                    ' each restore.'
                                    ' --quick skips this backup.')


    def makeBackup(self):
        ''' Create a backup of the data and configuration for a zenoss install.
        getWhatYouCan == True means to continue without reporting errors even
        if this appears to be an incomplete zenoss install.
        '''
    
        # Create temp backup dir
        rootTempDir = tempfile.mkdtemp()
        tempDir = os.path.join(rootTempDir, self.BACKUP_DIR)
        os.mkdir(tempDir)
        
        # mysqldump to backup dir
        
        cmd = 'mysqldump -u%s -p%s --routines %s > %s' % (
                    self.options.dbuser,
                    (self.options.dbpass or ''),
                    self.options.dbname,
                    os.path.join(tempDir, 'events.sql'))
        if os.system(cmd):
            sys.stderr.write('The database "%s" does not appear to exist.\n' %
                                self.options.dbname)
            if self.options.restore \
                and not self.options.quick \
                and not self.doesMySqlDbExist():
                sys.stderr.write('You may wish to use --quick.\n')
            return -1
                    
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
        ''' Restore from a previous backup
        '''
        # Arguably it would be better to tear down all existing
        # data, files, etc before starting the restore instead of
        # doing it all piecemeal like this.  If a restore failed along the
        # way it would be clear what was restored and what wasn't.  As it
        # is, if a restore fails the installation might be left with a mix 
        # of restored and unrestored state.
        
        # Check for running processes
        i, o = os.popen2('ps -Ao pid,command '
                            '| grep python '
                            '| grep -v "zenbackup" '
                            '| grep -v "do not match self" '
                            '| egrep "zope|zeo"'
                            )
        try:
            if len(o.readlines()):
                print ('It looks like one or more zenoss processes are running.'
                        '  Please quit zenoss before attempting to restore.')
                sys.exit(-1)
        finally:        
            i.close()
            o.close()
        
        # Create temp dir and untar backup into it
        rootTempDir = tempfile.mkdtemp()
        cmd = 'tar xzfC %s %s' % (self.options.file, rootTempDir)
        if os.system(cmd): return -1
        tempDir = os.path.join(rootTempDir, self.BACKUP_DIR)
        
        # If there is not a Data.fs then create an empty one
        # Maybe should read file location/name from zeo.conf
        # but we're going to assume the standard location for now.
        if not os.path.isfile(os.path.join(self.zenhome, 'var', 'Data.fs')):
            os.system('zeoctl start')
            os.system('zeoctl stop')
        
        # Restore zopedb        
        repozoDir = os.path.join(tempDir, 'repozo')
        cmd ='repozo.py --recover --repository %s --output %s' % (
                    repozoDir,
                    os.path.join(self.zenhome, 'var', 'Data.fs'))
        if os.system(cmd): return -1

        # Copy etc files
        cmd = 'cp %s %s' % (os.path.join(tempDir, 'etc', '*'),
                            os.path.join(self.zenhome, 'etc'))
        if os.system(cmd): return -1
        
        # Copy perf files
        cmd = 'cp -r %s %s' % (os.path.join(tempDir, 'perf', '*'),
                            os.path.join(self.zenhome, 'perf'))
        if os.system(cmd): return -1
        
        # Create the mysql db if it doesn't exist already
        if self.createMySqlDb(): return -1
        
        # Restore the mysql tables
        cmd='mysql -u%s -p%s %s < %s' % (
                            self.options.dbuser,
                            self.options.dbpass or '',
                            self.options.dbname,
                            os.path.join(tempDir, 'events.sql'))
        if os.system(cmd): return -1
        
        # clean up
        cmd = 'rm -r %s' % rootTempDir
        if os.system(cmd): return -1
        
        return 0

    def createMySqlDb(self):
        ''' Create the mysql db if it does not exist
        '''
        # The original dbname is stored in the backup within dbname.txt
        # For now we ignore it and use the database specified on the command
        # line.
        
        # Try to create the mysql database, ignore failure if the database
        # aleady exists.
        #cmd = 'mysqladmin -u %s -p %s create %s' % (
        #            self.options.dbuser,
        #            self.options.dbpass or '',
        #            self.options.dbname)
        sql = 'create database if not exists %s' % self.options.dbname
        cmd = 'echo "%s" | mysql -u%s -p%s' % (
                    sql,
                    self.options.dbuser,
                    self.options.dbpass or '')
        result = os.system(cmd)
        if result not in [0, 256]:
            return -1
        return 0
    
    def doesMySqlDbExist(self):
        ''' Return true if the mysqldb appears to exist, false otherwise.
        '''
        cmd = 'echo "show databases" | mysql -u%s -p%s | grep %s' % (
                self.options.dbuser,
                self.options.dbpass or '',
                self.options.dbname)
        i, o = os.popen2(cmd)
        out = o.read()
        i.close()
        o.close()
        return out != ''

if __name__ == '__main__':

    # Instantiate ZenBackup to get access to options
    zb = ZenBackup()
    
    # Check for required fields
    required = ['dbname', 'dbuser']
    if zb.options.restore:
        required.append('file')
    missing = [a for a in required if not getattr(zb.options, a, None)]
    if missing:
        # Print usage message
        print 'You must provide %s for %s' % (
            (len(missing) == 1 and 'a value') or 'values', ', '.join(missing))
        zb.parser.print_help();
    else:
        if not zb.options.dbpass:
            zb.options.dbpass = getpass.getpass(
                    'MySQL password for %s: ' % zb.options.dbuser)
        if zb.options.restore:
            # Perform restore, maybe doing a backup first
            if zb.options.quick or not zb.makeBackup():
                zb.restore()
        else:
            # Perform backup
            zb.makeBackup()
        
        