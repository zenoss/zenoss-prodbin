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


__doc__='''zenrestore

Restores a zenoss backup created by zenbackup.
'''

import Globals
import sys
import os
import os.path
import ConfigParser

from ZenBackupBase import *


class ZenRestore(ZenBackupBase):
        

    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZenBackupBase.buildOptions(self)
        
        self.parser.add_option('--dbname',
                               dest='dbname',
                               default=None,
                               help='MySQL events database name.  Defaults'
                                    ' to value saved with backup or "events"')
        self.parser.add_option('--dbuser',
                               dest='dbuser',
                               default=None,
                               help='MySQL username.  Defaults'
                                    ' to value saved with backup or "zenoss"')
        self.parser.add_option('--dbpass',
                               dest='dbpass',
                               default=None,
                               help='MySQL password. Defaults'
                                    ' to value saved with backup')
        self.parser.add_option('--file',
                               dest="file",
                               default=None,
                               help='File from which to restore.')
        self.parser.add_option('--dir',
                               dest="dir",
                               default=None,
                               help='Path to an untarred backup file'
                                        ' from which to restore.')
        self.parser.add_option('--no-eventsdb',
                               dest="noEventsDb",
                               default=False,
                               action='store_true',
                               help='Do not restore the events database.')


    def getSettings(self, tempDir):
        ''' Retrieve some options from settings file
        '''
        try:
            f = open(os.path.join(tempDir, CONFIG_FILE), 'r')
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


    def createMySqlDb(self):
        ''' Create the mysql db if it does not exist
        '''
        # The original dbname is stored in the backup within dbname.txt
        # For now we ignore it and use the database specified on the command
        # line.
        # 
        sql = 'create database if not exists %s' % self.options.dbname
        cmd = 'echo "%s" | mysql -u"%s" %s' % (
                    sql,
                    self.options.dbuser,
                    self.getPassArg())
        result = os.system(cmd)
        self.msg('db check returned %s' % result)
        if result not in [0, 256]:
            return -1
        return 0


    def doRestore(self):
        ''' Restore from a previous backup
        '''
        
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
                sys.stderr('The specified backup file does not exist: %s\n' %
                                self.options.file)
                sys.exit(-1)
            # Create temp dir and untar backup into it
            self.msg('Unpacking backup file')
            rootTempDir = self.getTempDir()
            cmd = 'tar xzfC %s %s' % (self.options.file, rootTempDir)
            if os.system(cmd): return -1
            tempDir = os.path.join(rootTempDir, BACKUP_DIR)
        else:
            self.msg('Using %s as source of restore' % self.options.dir)
            if not os.path.isdir(self.options.dir):
                sys.stderr('The specified backup directory does not exist:'
                                ' %s\n' % self.options.dir)
                sys.exit(-1)
            tempDir = self.options.dir
        
        # Maybe use values from backup file as defaults for self.options.
        self.getSettings(tempDir)
        if not self.options.dbname:
            self.options.dbname = 'events'
        if not self.options.dbuser:
            self.options.dbuser = 'zenoss'

        # If there is not a Data.fs then create an empty one
        # Maybe should read file location/name from zeo.conf
        # but we're going to assume the standard location for now.
        if not os.path.isfile(os.path.join(self.zenhome, 'var', 'Data.fs')):
            self.msg('There does not appear to be a zeo database.'
                        ' Starting zeo to create one.')
            os.system(os.path.join(self.zenhome, 'bin', 'zeoctl start > /dev/null'))
            os.system(os.path.join(self.zenhome, 'bin', 'zeoctl stop > /dev/null'))
        
        # Restore zopedb
        self.msg('Restoring the zeo database.')
        repozoDir = os.path.join(tempDir, 'repozo')
        cmd ='%s --recover --repository %s --output %s' % (
                    os.path.join(self.zenhome, 'bin', 'repozo.py'),
                    repozoDir,
                    os.path.join(self.zenhome, 'var', 'Data.fs'))
        if os.system(cmd): return -1
    
        # Copy etc files
        self.msg('Restoring config files.')
        cmd = 'rm -rf %s' % os.path.join(self.zenhome, 'etc')
        if os.system(cmd): return -1
        cmd = 'tar Cxf %s %s' % (
                        self.zenhome,
                        os.path.join(tempDir, 'etc.tar'))
        if os.system(cmd): return -1
        
        # Copy perf files
        self.msg('Restoring performance data.')
        cmd = 'rm -rf %s' % os.path.join(self.zenhome, 'perf')
        if os.system(cmd): return -1
        cmd = 'tar Cxf %s %s' % (
                        self.zenhome,
                        os.path.join(tempDir, 'perf.tar'))
        if os.system(cmd): return -1
        
        if self.options.noEventsDb:
            self.msg('Skipping the events database.')
        else:
            eventsSql = os.path.join(tempDir, 'events.sql')
            if os.path.isfile(eventsSql):
                # Create the mysql db if it doesn't exist already
                self.msg('Checking that events database exists.')
                if self.createMySqlDb(): return -1
        
                # Restore the mysql tables
                self.msg('Restoring events database.')
                cmd='mysql -u"%s" %s %s < %s' % (
                                    self.options.dbuser,
                                    self.getPassArg(),
                                    self.options.dbname,
                                    os.path.join(tempDir, 'events.sql'))
                if os.system(cmd): return -1
            else:
                self.msg('This backup does not contain an events database.')
        
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
        
    
