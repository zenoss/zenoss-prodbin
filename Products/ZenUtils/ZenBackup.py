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


__doc__='''zenbackup

Creates backup of Zope data files, Zenoss conf files and the events database.
'''

import sys
import os
import os.path
from datetime import date
from subprocess import Popen, PIPE
import time
import logging
import ConfigParser
import tarfile

import Globals
from ZCmdBase import ZCmdBase
from Products.ZenUtils.Utils import zenPath, binPath, readable_time
from ZenBackupBase import *


MAX_UNIQUE_NAME_ATTEMPTS = 1000


class ZenBackup(ZenBackupBase):

    def __init__(self):
        ZenBackupBase.__init__(self)
        self.log = logging.getLogger("zenbackup")
        logging.basicConfig()
        self.log.setLevel(self.options.logseverity)

    def runCommand(self, cmd=[], obfuscated_cmd=None):
        """
        Execute a command and return the results, displaying pre and
        post messages.

        @parameter cmd: command to run
        @type cmd: list
        @return: results of the command (output, warnings, returncode)
        """
        if obfuscated_cmd:
            self.log.debug(' '.join(obfuscated_cmd))
        else:
           self.log.debug(' '.join(cmd))

        proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
        output, warnings = proc.communicate()
        if proc.returncode:
            self.log.error(warnings)
        self.log.debug(output or 'No output from command')
        return (output, warnings, proc.returncode)


    def isZeoUp(self):
        '''
        Returns True if Zeo appears to be running, false otherwise.

        @return: whether Zeo is up or not
        @rtype: boolean
        '''
        # zeoup.py should live in either $ZOPEHOME/lib/bin/ (for the
        # appliance) or in $ZENHOME/bin (other installs.)
        cmd = [ binPath('python'), binPath('zeoup.py') ]
        cmd += '-p 8100 -h localhost'.split()
        self.log.debug("Can we access ZODB through Zeo?")

        (output, warnings, returncode) = self.runCommand(cmd)
        if returncode:
            return False
        return output.startswith('Elapsed time:')


    def readSettingsFromZeo(self):
        '''
        Store the dbname, dbuser, dbpass from saved settings in the Event
        Manager (ie ZODB) to the 'options' parsed object.
        '''
        zcmd = ZCmdBase(noopts=True)
        zem = zcmd.dmd.ZenEventManager
        for key, default, zemAttr in CONFIG_FIELDS:
            if not getattr(self.options, key, None):
                setattr(self.options, key,
                            getattr(zem, zemAttr, None) or default)


    def saveSettings(self):
        '''
        Save the database credentials to a file for use during restore.
        '''
        config = ConfigParser.SafeConfigParser()
        config.add_section(CONFIG_SECTION)
        config.set(CONFIG_SECTION, 'dbname', self.options.dbname)
        config.set(CONFIG_SECTION, 'dbuser', self.options.dbuser)
        if self.options.dbpass != None:
            config.set(CONFIG_SECTION, 'dbpass', self.options.dbpass)

        creds_file = os.path.join(self.tempDir, CONFIG_FILE)
        self.log.debug("Writing MySQL credentials to %s", creds_file)
        f = open(creds_file, 'w')
        try:
            config.write(f)
        finally:
            f.close()


    def getPassArg(self):
        '''
        Return string to be used as the -p (including the "-p")
        to MySQL commands.  Overrides the one in ZenBackupBase

        @return: password and flag
        @rtype: string
        '''
        if self.options.dbpass == None:
            return ''
        return '--password=%s' % self.options.dbpass

    def getDefaultBackupFile(self):
        """
        Return a name for the backup file or die trying.

        @return: unique name for a backup
        @rtype: string
        """
        def getName(index=0):
            """
            Try to create an unique backup file name.

            @return: tar file name
            @rtype: string
            """
            return 'zenbackup_%s%s.tgz' % (date.today().strftime('%Y%m%d'),
                                            (index and '_%s' % index) or '')
        backupDir = zenPath('backups')
        if not os.path.exists(backupDir):
            os.mkdir(backupDir, 0750)
        for i in range(MAX_UNIQUE_NAME_ATTEMPTS):
            name = os.path.join(backupDir, getName(i))
            if not os.path.exists(name):
                break
        else:
            self.log.critical('Cannot determine an unique file name to use'
                    ' in the backup directory (%s).' % backupDir +
                    ' Use --outfile to specify location for the backup'
                    ' file.\n')
            sys.exit(-1)
        return name


    def buildOptions(self):
        """
        Basic options setup
        """
        # pychecker can't handle strings made of multiple tokens
        __pychecker__ = 'no-noeffect no-constCond'
        ZenBackupBase.buildOptions(self)
        self.parser.add_option('--dbname',
                               dest='dbname',
                               default=None,
                               help='MySQL events database name.'
                                ' By default this will be fetched from Zenoss'
                                ' unless --dont-fetch-args is set.'),
        self.parser.add_option('--dbuser',
                               dest='dbuser',
                               default=None,
                               help='MySQL username.'
                                ' By default this will be fetched from Zenoss'
                                ' unless --dont-fetch-args is set.'),
        self.parser.add_option('--dbpass',
                               dest='dbpass',
                               default=None,
                               help='MySQL password.'
                                ' By default this will be fetched from Zenoss'
                                ' unless --dont-fetch-args is set.'),
        self.parser.add_option('--dont-fetch-args',
                                dest='fetchArgs',
                                default=True,
                                action='store_false',
                                help='By default dbname, dbuser and dbpass'
                                    ' are retrieved from Zenoss if not'
                                    ' specified and if Zenoss is available.'
                                    ' This disables fetching of these values'
                                    ' from Zenoss.')
        self.parser.add_option('--file',
                               dest="file",
                               default=None,
                               help='Name of file in which the backup will be stored.'
                                     ' Backups will by default be placed'
                                     ' in $ZENHOME/backups/')
        self.parser.add_option('--no-eventsdb',
                               dest="noEventsDb",
                               default=False,
                               action='store_true',
                               help='Do not include the events database'
                                    ' in the backup.')
        self.parser.add_option('--no-zodb',
                               dest="noZopeDb",
                               default=False,
                               action='store_true',
                               help='Do not include the ZODB'
                                    ' in the backup.')
        self.parser.add_option('--no-perfdata',
                               dest="noPerfData",
                               default=False,
                               action='store_true',
                               help='Do not include performance data'
                                    ' in the backup.')
        self.parser.add_option('--stdout',
                               dest="stdout",
                               default=False,
                               action='store_true',
                               help='Send backup to stdout instead of to a file.')
        self.parser.add_option('--save-mysql-access',
                                dest='saveSettings',
                                default=False,
                                action='store_true',
                                help='Include dbname, dbuser and dbpass'
                                    ' in the backup'
                                    ' file for use during restore.')

        self.parser.remove_option('-v')
        self.parser.add_option('-v', '--logseverity',
                        dest='logseverity',
                        default=20,
                        type='int',
                        help='Logging severity threshold')


    def backupEventsDatabase(self):
        """
        Backup the MySQL events database
        """
        partBeginTime = time.time()

        # Setup defaults for db info
        if self.options.fetchArgs and not self.options.noEventsDb:
            if self.isZeoUp():
                self.log.info('Getting MySQL dbname, user, password from ZODB.')
                self.readSettingsFromZeo()
            else:
                self.log.error('Unable to get MySQL credentials from ZODB.'
                            ' Zeo may not be available.')
                self.log.info("Skipping events database backup.")
                return

        if not self.options.dbname:
            self.options.dbname = 'events'
        if not self.options.dbuser:
            self.options.dbuser = 'zenoss'
        # A passwd of '' might be valid.  A passwd of None is interpreted
        # as no password.

        # Save options to a file for use during restore
        if self.options.saveSettings:
            self.saveSettings()

        self.log.info('Backing up events database.')
        cmd_p1 = ['mysqldump', '-u%s' % self.options.dbuser]
        cmd_p2 = ["--single-transaction", '--routines', self.options.dbname,
                  '--result-file=' + os.path.join(self.tempDir, 'events.sql') ]
        cmd = cmd_p1 + [self.getPassArg()] + cmd_p2
        obfuscated_cmd = cmd_p1 + ['*' * len(self.getPassArg())] + cmd_p2

        (output, warnings, returncode) = self.runCommand(cmd, obfuscated_cmd)
        if returncode:
            self.log.info("Backup terminated abnormally.")
            return -1

        partEndTime = time.time()
        subtotalTime = readable_time(partEndTime - partBeginTime)
        self.log.info("Backup of events database completed in %s.",
                          subtotalTime)


    def backupZODB(self):
        """
        Backup the Zope database.
        """
        partBeginTime = time.time()

        self.log.info('Backing up the ZODB.')
        repozoDir = os.path.join(self.tempDir, 'repozo')
        os.mkdir(repozoDir, 0750)
        cmd = [binPath('python'), binPath('repozo.py'),
                '--repository', repozoDir, '--file',
                zenPath('var', 'Data.fs'),
                '--backup', '--full' ]
        (output, warnings, returncode) = self.runCommand(cmd)
        if returncode:
            self.log.critical("Backup terminated abnormally.")
            return -1

        partEndTime = time.time()
        subtotalTime = readable_time(partEndTime - partBeginTime)
        self.log.info("Backup of ZODB database completed in %s.", subtotalTime)


    def backupPerfData(self):
        """
        Back up the RRD files storing performance data.
        """
        perfDir = zenPath('perf')
        if not os.path.isdir(perfDir):
            self.log.warning('%s does not exist, skipping.', perfDir)
            return

        partBeginTime = time.time()

        self.log.info('Backing up performance data (RRDs).')
        tarFile = os.path.join(self.tempDir, 'perf.tar')
        cmd = ['tar', 'cf', tarFile, perfDir]
        (output, warnings, returncode) = self.runCommand(cmd)
        if returncode:
            self.log.critical("Backup terminated abnormally.")
            return -1

        partEndTime = time.time()
        subtotalTime = readable_time(partEndTime - partBeginTime)
        self.log.info("Backup of performance data completed in %s.",
                      subtotalTime )


    def packageStagingBackups(self):
        """
        Gather all of the other data into one nice, neat file for easy
        tracking.
        """
        self.log.info('Packaging backup file.')
        if self.options.file:
            outfile = self.options.file
        else:
            outfile = self.getDefaultBackupFile()
        tempHead, tempTail = os.path.split(self.tempDir)
        tarFile = outfile
        if self.options.stdout:
            tarFile = '-'
        cmd = ['tar', 'czfC', tarFile, tempHead, tempTail]
        (output, warnings, returncode) = self.runCommand(cmd)
        if returncode:
            self.log.critical("Backup terminated abnormally.")
            return -1
        self.log.info('Backup written to %s' % outfile)


    def cleanupTempDir(self):
        """
        Remove temporary files in staging directory.
        """
        self.log.info('Cleaning up staging directory %s' % self.rootTempDir)
        cmd = ['rm', '-r', self.rootTempDir]
        (output, warnings, returncode) = self.runCommand(cmd)
        if returncode:
            self.log.critical("Backup terminated abnormally.")
            return -1


    def makeBackup(self):
        '''
        Create a backup of the data and configuration for a Zenoss install.
        '''
        backupBeginTime = time.time()

        # Create temp backup dir
        self.rootTempDir = self.getTempDir()
        self.tempDir = os.path.join(self.rootTempDir, BACKUP_DIR)
        self.log.debug("Use %s as a staging directory for the backup", self.tempDir)
        os.mkdir(self.tempDir, 0750)

        if self.options.noEventsDb:
            self.log.info('Skipping backup of events database.')
        else:
            self.backupEventsDatabase()

        if self.options.noZopeDb:
            self.log.info('Skipping backup of ZODB.')
        else:
            self.backupZODB()

        # Copy /etc to backup dir (except for sockets)
        self.log.info('Backing up config files.')
        etcTar = tarfile.open(os.path.join(self.tempDir, 'etc.tar'), 'w')
        etcTar.add(zenPath('etc'), 'etc')
        etcTar.close()
        self.log.info("Backup of config files completed.")
        
        # Copy /ZenPacks to backup dir
        self.log.info('Backing up ZenPacks.')
        etcTar = tarfile.open(os.path.join(self.tempDir, 'ZenPacks.tar'), 'w')
        etcTar.add(zenPath('ZenPacks'), 'ZenPacks')
        etcTar.close()
        self.log.info("Backup of ZenPacks completed.")

        if self.options.noPerfData:
            self.log.info('Skipping backup of performance data.')
        else:
            self.backupPerfData()

        # tar, gzip and send to outfile
        self.packageStagingBackups()

        self.cleanupTempDir()

        backupEndTime = time.time()
        totalBackupTime = readable_time(backupEndTime - backupBeginTime)
        self.log.info('Backup completed successfully in %s.', totalBackupTime)
        return 0


if __name__ == '__main__':
    zb = ZenBackup()
    if zb.makeBackup():
        sys.exit(-1)
