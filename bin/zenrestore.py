#! /usr/bin/env python 
#################################################################
#
#   Copyright (c) 2007 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''zenrestore

Restores a zenoss backup created by zenbackup.
'''

import Globals
from Products.ZenUtils.CmdBase import CmdBase
import sys
import os
import os.path
import tempfile
import ConfigParser

from zenbackupcommon import *


class ZenRestore(CmdBase):


    def __init__(self, noopts=0):
        CmdBase.__init__(self, noopts)
        self.zenhome = os.getenv('ZENHOME')
        

    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        CmdBase.buildOptions(self)
        
        self.parser.add_option('--dbname',
                               dest='dbname',
                               default=None,
                               help='MySQL events database name.  Defaults'
                                    ' to value saved with backup or "events"')
        self.parser.add_option('--dbuser',
                               dest='dbuser',
                               default=None,
                               help='MySQL username.  Defaults'
                                    ' to value saved with backup or "root"')
        self.parser.add_option('--dbpass',
                               dest='dbpass',
                               default=None,
                               help='MySQL password. Defaults'
                                    ' to value saved with backup')
        self.parser.add_option('--file',
                               dest="file",
                               default=None,
                               help='File to restore from.')


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
            if not getattr(self.options, key, None):
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
        sql = 'create database if not exists %s' % self.options.dbname
        cmd = 'echo "%s" | mysql -u%s -p%s' % (
                    sql,
                    self.options.dbuser,
                    self.options.dbpass or '')
        result = os.system(cmd)
        if result not in [0, 256]:
            return -1
        return 0


    def doRestore(self):
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
        tempDir = os.path.join(rootTempDir, BACKUP_DIR)
        
        # Maybe use values from backup file as defaults for self.options.
        self.getSettings(tempDir)
                
        # If there is not a Data.fs then create an empty one
        # Maybe should read file location/name from zeo.conf
        # but we're going to assume the standard location for now.
        if not os.path.isfile(os.path.join(self.zenhome, 'var', 'Data.fs')):
            os.system(os.path.join(self.zenhome, 'bin', 'zeoctl start'))
            os.system(os.path.join(self.zenhome, 'bin', 'zeoctl stop'))
        
        # Restore zopedb        
        repozoDir = os.path.join(tempDir, 'repozo')
        cmd ='%s --recover --repository %s --output %s' % (
                    os.path.join(self.zenhome, 'bin', 'repozo.py'),
                    repozoDir,
                    os.path.join(self.zenhome, 'var', 'Data.fs'))
        if os.system(cmd): return -1
    
        # Copy etc files
        cmd = 'rm -rf %s' % os.path.join(self.zenhome, 'etc')
        if os.system(cmd): return -1
        cmd = 'tar Cxf %s %s' % (
                        self.zenhome,
                        os.path.join(tempDir, 'etc.tar'))
        if os.system(cmd): return -1
        
        # Copy perf files
        cmd = 'rm -rf %s' % os.path.join(self.zenhome, 'perf')
        if os.system(cmd): return -1
        cmd = 'tar Cxf %s %s' % (
                        self.zenhome,
                        os.path.join(tempDir, 'perf.tar'))
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


if __name__ == '__main__':
    zb = ZenRestore()
    
    if not zb.options.file:
        print 'You must specify a backup file to restore from using' + \
                ' the --flag option.'
        sys.exit(-1)
    if (zb.doRestore()): sys.exit(-1)
