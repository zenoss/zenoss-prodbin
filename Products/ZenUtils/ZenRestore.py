#! /usr/bin/env python
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2009 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__='''zenrestore

Restores a zenoss backup created by zenbackup.
'''

import logging
import sys
import os
import os.path
import subprocess
import tarfile
import ConfigParser

import Globals
from Products.ZenUtils.Utils import zenPath, binPath

from ZenBackupBase import *


class ZenRestore(ZenBackupBase):

    def __init__(self):
        ZenBackupBase.__init__(self)
        self.log = logging.getLogger("zenrestore")
        logging.basicConfig()
        if self.options.verbose:
            self.log.setLevel(10)
        else:
            self.log.setLevel(40)

    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZenBackupBase.buildOptions(self)

        self.parser.add_option('--dbname',
                               dest='dbname',
                               default=None,
                               help='MySQL events database name.  Defaults'
                                    ' to value saved with backup or "events".')
        self.parser.add_option('--dbuser',
                               dest='dbuser',
                               default=None,
                               help='MySQL username.  Defaults'
                                    ' to value saved with backup or "zenoss".')
        self.parser.add_option('--dbpass',
                               dest='dbpass',
                               default=None,
                               help='MySQL password. Defaults'
                                    ' to value saved with backup.')
        self.parser.add_option('--dbhost',
                               dest='dbhost',
                               default='localhost',
                               help='MySQL server host.'
                                ' Defaults to value saved with backup.'),
        self.parser.add_option('--dbport',
                               dest='dbport',
                               default='3306',
                               help='MySQL server port number.'
                                ' Defaults to value saved with backup.'),
        self.parser.add_option('--file',
                               dest="file",
                               default=None,
                               help='File from which to restore.')
        self.parser.add_option('--dir',
                               dest="dir",
                               default=None,
                               help='Path to an untarred backup file'
                                        ' from which to restore.')
        self.parser.add_option('--no-zodb',
                               dest="noZODB",
                               default=False,
                               action='store_true',
                               help='Do not restore the ZODB.')
        self.parser.add_option('--no-eventsdb',
                               dest="noEventsDb",
                               default=False,
                               action='store_true',
                               help='Do not restore the events database.')
        self.parser.add_option('--no-perfdata',
                               dest="noPerfdata",
                               default=False,
                               action='store_true',
                               help='Do not restore performance data.')
        self.parser.add_option('--deletePreviousPerfData',
                               dest="deletePreviousPerfData",
                               default=False,
                               action='store_true',
                               help='Delete ALL existing performance data before restoring?')
        self.parser.add_option('--zenpacks',
                               dest='zenpacks',
                               default=False,
                               action='store_true',
                               help=('Experimental: Restore any ZenPacks in ' 
                                     'the backup. Some ZenPacks may not work '
                                     'properly. Reinstall ZenPacks if possible'))

    def getSettings(self):
        ''' Retrieve some options from settings file
        '''
        try:
            f = open(os.path.join(self.tempDir, CONFIG_FILE), 'r')
        except:
            return
        try:
            config = ConfigParser.SafeConfigParser()
            config.readfp(f)
        finally:
            f.close()
        for key, default, zemAttr in CONFIG_FIELDS:
            if getattr(self.options, key, None) == None:
                if config.has_option(CONFIG_SECTION, key):
                    setattr(self.options, key, config.get(CONFIG_SECTION, key))
                else:
                    setattr(self.options, key, default)


    def restoreMySqlDb(self, host, port, db, user, passwd, sqlFile):
        """
        Create MySQL database if it doesn't exist.
        """
        mysql_cmd = ['mysql', '-u%s' % user]
        mysql_cmd.extend(passwd)
        if host and host != 'localhost':
            mysql_cmd.extend(['--host', host])
        if port and str(port) != '3306':
            mysql_cmd.extend(['--port', str(port)])

        mysql_cmd = subprocess.list2cmdline(mysql_cmd)

        cmd = 'echo "create database if not exists %s" | %s' % (db, mysql_cmd)
        os.system(cmd)

        cmd = '%s %s < %s' % (
            mysql_cmd, db, os.path.join(self.tempDir, sqlFile)
        )
        os.system(cmd)


    def restoreEventsDatabase(self):
        """
        Restore the MySQL events database
        """
        eventsSql = os.path.join(self.tempDir, 'events.sql')
        if not os.path.isfile(eventsSql):
            self.msg('This backup does not contain an events database backup.')
            return

        self.msg('Restoring events database.')
        self.restoreMySqlDb(self.options.dbhost, self.options.dbport,
                            self.options.dbname, self.options.dbuser,
                            self.getPassArg('dbpass'), eventsSql)
    
    def restoreZEP(self):
        '''
        Restore ZEP DB and indexes
        '''
        zepSql = os.path.join(self.tempDir, 'zep.sql')
        if not os.path.isfile(zepSql):
            self.msg('This backup does not contain a ZEP database backup.')
            return
        
        self.msg('Restoring ZEP database.')
        self.restoreMySqlDb(self.options.zepdbhost, self.options.zepdbport,
                            self.options.zepdbname, self.options.zepdbuser,
                            self.getPassArg('zepdbpass'), zepSql)
        self.msg('ZEP database restored.')
        self.msg('Restoring ZEP indexes.')
        zepTar = tarfile.open(os.path.join(self.tempDir, 'zep.tar'))
        zepTar.extractall(zenPath('var'))
        self.msg('ZEP indexes restored.')
        

    def hasZeoBackup(self):
        repozoDir = os.path.join(self.tempDir, 'repozo')
        return os.path.isdir(repozoDir)

    def hasSqlBackup(self):
        return os.path.isfile(os.path.join(self.tempDir, 'zodb.sql'))

    def hasZODBBackup(self):
        return self.hasZeoBackup() or self.hasSqlBackup()

    def restoreZODB(self):
        if self.hasSqlBackup():
            self.restoreZODBSQL()
        elif self.hasZeoBackup():
            self.restoreZODBZEO()

    def restoreZODBSQL(self):
        zodbSql = os.path.join(self.tempDir, 'zodb.sql')
        if not os.path.isfile(zodbSql):
            self.msg('This archive does not contain a ZODB backup.')
            return
        self.msg('Restoring ZODB database.')
        self.restoreMySqlDb(self.options.host, self.options.port,
                            self.options.mysqldb, self.options.mysqluser,
                            self.getPassArg('mysqlpasswd'), zodbSql)

    def restoreZODBZEO(self):
        repozoDir = os.path.join(self.tempDir, 'repozo')
        tempFilePath = os.path.join(self.tempDir, 'Data.fs')
        tempZodbConvert = os.path.join(self.tempDir, 'convert.conf')

        self.msg('Restoring ZEO backup into MySQL.')

        # Create a Data.fs from the repozo backup
        cmd = []
        cmd.append(binPath('repozo'))
        cmd.append('--recover')
        cmd.append('--repository')
        cmd.append(repozoDir)
        cmd.append('--output')
        cmd.append(tempFilePath)

        rc = subprocess.call(cmd, stdout=PIPE, stderr=PIPE)
        if rc:
            return -1

        # Now we have a Data.fs, restore into MySQL with zodbconvert
        zodbconvert_conf = open(tempZodbConvert, 'w')
        zodbconvert_conf.write('<filestorage source>\n')
        zodbconvert_conf.write('  path %s\n' % tempFilePath)
        zodbconvert_conf.write('</filestorage>\n\n')

        zodbconvert_conf.write('<relstorage destination>\n')
        zodbconvert_conf.write('  <mysql>\n')
        zodbconvert_conf.write('    host %s\n' % self.options.host)
        zodbconvert_conf.write('    port %s\n' % self.options.port)
        zodbconvert_conf.write('    db %s\n' % self.options.mysqldb)
        zodbconvert_conf.write('    user %s\n' % self.options.mysqluser)
        zodbconvert_conf.write('    passwd %s\n' % self.options.mysqlpasswd or '')
        zodbconvert_conf.write('  </mysql>\n')
        zodbconvert_conf.write('</relstorage>\n')
        zodbconvert_conf.close()

        rc = subprocess.call(['zodbconvert', '--clear', tempZodbConvert],
                             stdout=PIPE, stderr=PIPE)
        if rc:
            return -1


    def restoreEtcFiles(self):
        self.msg('Restoring config files.')
        cmd = 'cp -p %s %s' % (os.path.join(zenPath('etc'), 'global.conf'), self.tempDir)
        if os.system(cmd): return -1
        cmd = 'rm -rf %s' % zenPath('etc')
        if os.system(cmd): return -1
        cmd = 'tar Cxf %s %s' % (
            zenPath(),
            os.path.join(self.tempDir, 'etc.tar')
        )
        if os.system(cmd): return -1
        if not os.path.exists(os.path.join(zenPath('etc'), 'global.conf')):
            self.msg('Restoring default global.conf')
            cmd = 'mv %s %s' % (os.path.join(self.tempDir, 'global.conf'), zenPath('etc'))
            if os.system(cmd): return -1

    def restoreZenPacks(self):
        self.msg('Restoring ZenPacks.')
        cmd = 'rm -rf %s' % zenPath('ZenPacks')
        if os.system(cmd): return -1
        cmd = 'tar Cxf %s %s' % (
                        zenPath(),
                        os.path.join(self.tempDir, 'ZenPacks.tar'))
        if os.system(cmd): return -1
        # restore bin dir when restoring zenpacks
        #make sure bin dir is in tar
        tempBin = os.path.join(self.tempDir, 'bin.tar')
        if os.path.isfile(tempBin):
            self.msg('Restoring bin dir.')
            #k option prevents overwriting existing bin files
            cmd = ['tar', 'Cxfk', zenPath(),
                   os.path.join(self.tempDir, 'bin.tar')]
            self.runCommand(cmd)

    def restorePerfData(self):
        cmd = 'rm -rf %s' % os.path.join(zenPath(), 'perf')
        if os.system(cmd): return -1
        self.msg('Restoring performance data.')
        cmd = 'tar Cxf %s %s' % (
                        zenPath(),
                        os.path.join(self.tempDir, 'perf.tar'))
        if os.system(cmd): return -1

    def doRestore(self):
        """
        Restore from a previous backup
        """
        if self.options.file and self.options.dir:
            sys.stderr.write('You cannot specify both --file and --dir.\n')
            sys.exit(-1)
        elif not self.options.file and not self.options.dir:
            sys.stderr.write('You must specify either --file or --dir.\n')
            sys.exit(-1)

        # Maybe check to see if zeo is up and tell user to quit zenoss first

        rootTempDir = ''
        if self.options.file:
            if not os.path.isfile(self.options.file):
                sys.stderr.write('The specified backup file does not exist: %s\n' %
                      self.options.file)
                sys.exit(-1)
            # Create temp dir and untar backup into it
            self.msg('Unpacking backup file')
            rootTempDir = self.getTempDir()
            cmd = 'tar xzfC %s %s' % (self.options.file, rootTempDir)
            if os.system(cmd): return -1
            self.tempDir = os.path.join(rootTempDir, BACKUP_DIR)
        else:
            self.msg('Using %s as source of restore' % self.options.dir)
            if not os.path.isdir(self.options.dir):
                sys.stderr.write('The specified backup directory does not exist:'
                                ' %s\n' % self.options.dir)
                sys.exit(-1)
            self.tempDir = self.options.dir

        # Maybe use values from backup file as defaults for self.options.
        self.getSettings()
        if not self.options.dbname:
            self.options.dbname = 'events'
        if not self.options.dbuser:
            self.options.dbuser = 'zenoss'

        if self.options.zenpacks and not self.hasZODBBackup():
            sys.stderr.write('Archive does not contain ZODB backup; cannot'
                             'restore ZenPacks')
            sys.exit(-1)

        # ZODB
        if self.hasZODBBackup():
            self.restoreZODB()
        else:
            self.msg('Archive does not contain a ZODB backup')

        # Configuration
        self.restoreEtcFiles()

        # ZenPacks
        if self.options.zenpacks:
            tempPacks = os.path.join(self.tempDir, 'ZenPacks.tar')
            if os.path.isfile(tempPacks):
                self.restoreZenPacks()
            else:
                self.msg('Backup contains no ZenPacks.')

        # Performance Data
        tempPerf = os.path.join(self.tempDir, 'perf.tar')
        if os.path.isfile(tempPerf):
            self.restorePerfData()
        else:
            self.msg('Backup contains no perf data.')

        # Events
        if self.options.noEventsDb:
            self.msg('Skipping the events database.')
        else:
            self.restoreEventsDatabase()
            self.restoreZEP()

        # clean up
        if self.options.file:
            self.msg('Cleaning up temporary files.')
            cmd = 'rm -r %s' % rootTempDir
            if os.system(cmd): return -1

        self.msg('Restore complete.')
        return 0


if __name__ == '__main__':
    zb = ZenRestore()
    if zb.doRestore():
        sys.exit(-1)
