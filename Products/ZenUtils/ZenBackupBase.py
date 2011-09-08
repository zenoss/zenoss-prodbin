#! /usr/bin/env python
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2009 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################


__doc__='''ZenBackupBase

Common code for zenbackup.py and zenrestore.py
'''
import tempfile
from subprocess import Popen, PIPE

from CmdBase import CmdBase


BACKUP_DIR = 'zenbackup'
CONFIG_FILE = 'backup.settings'
CONFIG_SECTION = 'zenbackup'

class ZenBackupBase(CmdBase):
    doesLogging = False


    def __init__(self, noopts=0):
        CmdBase.__init__(self, noopts)

    def msg(self, msg):
        '''
        If --verbose then send msg to stdout
        '''
        if self.options.verbose:
            print(msg)


    def buildOptions(self):
        """
        Command-line options setup
        """
        CmdBase.buildOptions(self)
        self.parser.add_option('-v', '--verbose',
                               dest="verbose",
                               default=False,
                               action='store_true',
                               help='Send progress messages to stdout.')
        self.parser.add_option('--temp-dir',
                               dest="tempDir",
                               default=None,
                               help='Directory to use for temporary storage.')
        self.parser.add_option('--host',
                    dest="host",default="localhost",
                    help="hostname of MySQL object store")
        self.parser.add_option('--port',
                    dest="port", default='3306',
                    help="port of MySQL object store")
        self.parser.add_option('--mysqluser', dest='mysqluser', default='zenoss',
                    help='username for MySQL object store')
        self.parser.add_option('--mysqlpasswd', dest='mysqlpasswd', default='zenoss',
                    help='passwd for MySQL object store')
        self.parser.add_option('--mysqldb', dest='mysqldb', default='zodb',
                    help='Name of database for MySQL object store')
        self.parser.add_option('--cacheservers', dest='cacheservers',
                    help='memcached servers to use for object cache (eg. 127.0.0.1:11211)')
        self.parser.add_option('--zepdbname',
                               dest='zepdbname',
                               default='zenoss_zep',
                               help='ZEP database name.'
                                ' By default this will be fetched from Zenoss'
                                ' unless --dont-fetch-args is set.'),
        self.parser.add_option('--zepdbuser',
                               dest='zepdbuser',
                               default='zenoss',
                               help='ZEP database username.'
                                ' By default this will be fetched from Zenoss'
                                ' unless --dont-fetch-args is set.'),
        self.parser.add_option('--zepdbpass',
                               dest='zepdbpass',
                               default='zenoss',
                               help='ZEP database password.'
                                ' By default this will be fetched from Zenoss'
                                ' unless --dont-fetch-args is set.'),
        self.parser.add_option('--zepdbhost',
                               dest='zepdbhost',
                               default='localhost',
                               help='ZEP database server host.'
                                ' By default this will be fetched from Zenoss'
                                ' unless --dont-fetch-args is set.'),
        self.parser.add_option('--zepdbport',
                               dest='zepdbport',
                               default='3306',
                               help='ZEP database server port number.'
                                ' By default this will be fetched from Zenoss'
                                ' unless --dont-fetch-args is set.'),
        self.parser.add_option('--compress-transport',
                               dest="compressTransport",
                               default=True,
                               help='Compress transport for MySQL backup/restore.'
                               ' True by default, set to False to disable over'
                               ' fast links that do not benefit from compression.')


    def getPassArg(self, optname='dbpass'):
        """
        Return string to be used as the -p (including the "-p")
        to MySQL commands.

        @return: password and flag
        @rtype: string
        """
        password = getattr(self.options, optname, None)
        if not password:
            return []
        return ['-p%s' % password]


    def getTempDir(self):
        """
        Return directory to be used for temporary storage
        during backup or restore.

        @return: directory name
        @rtype: string
        """
        if self.options.tempDir:
            dir = tempfile.mkdtemp('', '', self.options.tempDir)
        else:
            dir = tempfile.mkdtemp()
        return dir


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
            self.log.warn(warnings)
        self.log.debug(output or 'No output from command')
        return (output, warnings, proc.returncode)

    def runMysqlCmd(self, sql, switchDB=False):
        """
        Run a command that executes SQL statements in MySQL.
        Return true if the command was able to complete, otherwise
        (eg permissions or login error), return false.

        @parameter sql: an executable SQL statement
        @type sql: string
        @parameter switchDB: use -D options.dbname to switch to a database?
        @type switchDB: boolean
        @return: boolean
        @rtype: boolean
        """
        cmd = ['mysql', '-u', self.options.dbuser]

        obfuscatedCmd = None
        if self.options.dbpass:
            cmd.append('--password=%s' % self.options.dbpass)

        if self.options.dbhost and self.options.dbhost != 'localhost':
            cmd.append('--host=%s' % self.options.dbhost)
        if self.options.dbport and self.options.dbport != '3306':
            cmd.append('--port=%s' % self.options.dbport)

        if switchDB:
            cmd.extend(['-D', self.options.dbname])

        cmd.extend(['-e', sql])

        if self.options.dbpass:
            obfuscatedCmd = cmd[:]
            obfuscatedCmd[3] = '--pasword=%s' % ('*' * 8)

        result = self.runCommand(cmd, obfuscated_cmd=obfuscatedCmd)
        if result[2]: # Return code from the command
            return False
        return True

