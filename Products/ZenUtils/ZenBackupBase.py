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


__doc__='''zenbackupcommon.py

Common code for zenbackup.py and zenrestore.py
'''

import os
import tempfile
from CmdBase import CmdBase


BACKUP_DIR = 'zenbackup'
CONFIG_FILE = 'backup.settings'
CONFIG_SECTION = 'zenbackup'
CONFIG_FIELDS = (   ('dbname', 'events', 'database'),
                    ('dbuser', 'root', 'username'),
                    ('dbpass', '', 'password'))


class ZenBackupBase(CmdBase):


    doesLogging = False


    def __init__(self, noopts=0):
        CmdBase.__init__(self, noopts)
        self.zenhome = os.getenv('ZENHOME')


    def msg(self, msg):
        ''' If --verbose then send msg to stdout
        '''
        if self.options.verbose:
            print(msg)


    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
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


    def getPassArg(self):
        ''' Return string to be used as the -p (including the "-p")
        to mysql commands
        '''
        if self.options.dbpass == None:
            return ''
        return '-p"%s"' % self.options.dbpass


    def getTempDir(self):
        ''' Return directory to be used for temporary storage
        during backup or restore.
        '''
        if self.options.tempDir:
            dir = tempfile.mkdtemp('', '', self.options.tempDir)
        else:
            dir = tempfile.mkdtemp()
        return dir
