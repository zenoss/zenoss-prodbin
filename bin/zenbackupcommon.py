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
# This program is part of Zenoss Core, an open source monitoring platform.
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
# For complete information please visit: http://www.zenoss.com/oss/
# This program is part of Zenoss Core, an open source monitoring platform.
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
# For complete information please visit: http://www.zenoss.com/oss/
#! /usr/bin/env python 

__doc__='''zenbackupcommon.py

Common code for zenbackup.py and zenrestore.py
'''

BACKUP_DIR = 'zenbackup'

CONFIG_FILE = 'backup.settings'
CONFIG_SECTION = 'zenbackup'

CONFIG_FIELDS = (   ('dbname', 'events', 'database'),                    ('dbuser', 'root', 'username'),
                    ('dbpass', '', 'password'))
                
