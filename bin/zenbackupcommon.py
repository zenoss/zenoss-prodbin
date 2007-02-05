#! /usr/bin/env python 
#################################################################
#
#   Copyright (c) 2007 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''zenbackupcommon.py

Common code for zenbackup.py and zenrestore.py
'''

BACKUP_DIR = 'zenbackup'

CONFIG_FILE = 'backup.settings'
CONFIG_SECTION = 'zenbackup'

CONFIG_FIELDS = (   ('dbname', 'events', 'database'),
                    ('dbuser', 'root', 'username'),
                    ('dbpass', '', 'password'))
                
