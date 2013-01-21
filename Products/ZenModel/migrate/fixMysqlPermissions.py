##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

import textwrap

import Migrate

from Products.ZenUtils import GlobalConfig, ZenDB

class FixMysqlPermissions(Migrate.Step):
    " Fix mysql permissions so zep db backup won't die. "

    version = Migrate.Version(4, 2, 4)
    
    def cutover(self, dmd):
        db = ZenDB.ZenDB('zep', useAdmin=True)
        sql_cmd = textwrap.dedent('''
            GRANT SELECT ON mysql.proc TO '{zep-user}'@'{zep-host}';
            GRANT SELECT ON mysql.proc TO '{zep-user}'@'%';
            FLUSH PRIVILEGES;
        ''')
        d = GlobalConfig.globalConfToDict()
        db.executeSql(sql_cmd.format(**d))

FixMysqlPermissions()
