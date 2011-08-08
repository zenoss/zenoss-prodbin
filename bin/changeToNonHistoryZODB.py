#!/usr/bin/env python
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import Globals

from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from ZODB.POSException import StorageError
import os
import re
import sys
from tempfile import NamedTemporaryFile

class UpgradeManager(ZenScriptBase):
    """main driver for upgrading data store"""
    
    

    def __init__(self, noopts=0):
        ZenScriptBase.__init__(self, noopts=noopts, connect=False)
        
    def buildOptions(self):
        """build script specific options"""

        ZenScriptBase.buildOptions(self) # call baseclasses's buildOptions
        
        self.parser.add_option('--tempdb-host',
                    dest="tempdb_host",default=None,
                    help="host for temporary database, uses current zodb host if not specified")
        
        self.parser.add_option('--tempdb-port',
                    dest="tempdb_port",default=None,
                    help="port for temporary database, uses current zodb port if not specified")

        self.parser.add_option('--tempdb-socket',
                    dest="tempdb_socket",default=None,
                    help="unix socket for temporary database, uses current zodb socket if not specified")

        self.parser.add_option('--tempdb-user',
                    dest="tempdb_user",default='root',
                    help="user for temporary database, uses 'root' if not specified")

        self.parser.add_option('--tempdb-passwd',
                    dest="tempdb_passwd",default=None,
                    help="password for temporary database")

        self.parser.add_option('--tempdb-name',
                    dest="tempdb_name",default='zodb_temp',
                    help="name for temporary database")

        self.parser.add_option('--zodb-backup-path',
                    dest="zodb_backup_path",default='/tmp',
                    help="backup path for current zodb")

    def run(self):
        
        if self.relstorageIsHistoryFree():
            print "The currently configured relstorage instance is history free."
            print "No conversion required."
            sys.exit(0)
            
        print "History preserving relstorage detected."
        print self.backupDB()
        
        print "Copying current zodb to non-history preserving temp database"
        configFile = self.writeZodbConvertConfig()
        self.createTempDB()
        self.convertZodb(configFile)
        self.dropZodb()
        
        print "Restoring Production ZODB instance from temp db."
        self.restore()
        
    
    def writeZodbConvertConfig(self):
        params = self.getConnectionParameters(keyPrefix='source_', tempDB=False)
        params.update(self.getConnectionParameters(keyPrefix='destination_', tempDB=True))
        if params['source_passwd']:
            params['source_passwd'] = 'passwd ' + params['source_passwd']
        if params['destination_passwd']:
            params['destination_passwd'] = 'passwd ' + params['destination_passwd']
        if params['source_socket']:
            params['source_socket'] = 'unix_socket ' + params['source_socket']
        if params['destination_socket']:
            params['destination_socket'] = 'unix_socket ' + params['destination_socket']
        conf = """
<relstorage source>
    <mysql>
        host %(source_host)s
        port %(source_port)s
        db %(source_db)s
        user %(source_user)s
        %(source_passwd)s
        %(source_socket)s
    </mysql>
</relstorage>
<relstorage destination>
    keep-history false
    <mysql>
        host %(destination_host)s
        port %(destination_port)s
        db %(destination_db)s
        user %(destination_user)s
        %(destination_passwd)s
        %(destination_socket)s
    </mysql>
</relstorage>
"""
        zodbConvertConf = NamedTemporaryFile('w', prefix='zodbconvert_', suffix='.conf', delete=False)
        filename = zodbConvertConf.name
        zodbConvertConf.write(conf % params)
        zodbConvertConf.close()
        return filename


    def convertZodb(self, configFile):
        cmd = 'zodbconvert "%s"' % configFile
        print "Executing: %s" % cmd
        os.system(cmd)

    def restore(self):
        cmd = 'mysqldump %s | mysql %s "' % (
            self.createClientConnectionString(tempDB=True),
            self.createClientConnectionString(tempDB=False),
        )
        print "Restoring production ZODB from tempdb: %s " % cmd
        os.system(cmd)

    def dropZodb(self):
        cmd = 'mysql %s -e "drop database if exists %s; create database %s "' % (
            self.createClientConnectionString(db='', tempDB=True),
            self.options.mysqldb,
            self.options.mysqldb,
        )
        print "Dropping production ZODB: %s " % cmd
        os.system(cmd)
    
    def backupDB(self):
        destFilename = '%s/zodb.sql.gz' % self.options.zodb_backup_path
        if os.path.exists(destFilename):
            print "Backup file exists. Remove or move %r." % destFilename
            sys.exit(1)
        cmd = 'mysqldump --add-drop-table %s | gzip > "%s"' % (
            self.createClientConnectionString(),
            destFilename,
        )
        print "Backing up current ZODB: %s " % cmd
        os.system(cmd)
        
    def createTempDB(self):
        cmd = 'mysql %s -e "drop database if exists %s; create database %s "' % (
            self.createClientConnectionString(db='', tempDB=True),
            self.options.tempdb_name,
            self.options.tempdb_name,
        )
        print "Creating TempDB: %s " % cmd
        os.system(cmd)

    def createClientConnectionString(self, db=None,tempDB=False):
        params = self.getConnectionParameters(tempDB=tempDB)
        if params['passwd']:
            params['passwd'] = '-p%s' % params['passwd']
        if params['socket']:
            params['socket'] = '--socket="%s"' % params['socket']
        if db is not None:
            params['db'] = db
        cmdArgs = '--user="%(user)s" --host="%(host)s" %(db)s %(passwd)s %(socket)s' % params
        return cmdArgs
        
        
    def relstorageIsHistoryFree(self):
        """determine if currently configured relstorage connection is history free."""
        try:
            args = self.getConnectionParameters(tempDB=False)
            args['keep_history'] = False
            connection = getRelstorageConnection(**args)
        except StorageError as ex:
            msg = str(ex)
            if msg.startswith("Schema mismatch: a history-free adapter"):
                return False
            # unexpected error
            raise ex
        # connected with history free adaptor and received no errors
        # this relstorage instance must be history free!
        return True

    def getConnectionParameters(self, keyPrefix='', tempDB=False):
        
        if tempDB:
            # create the tempdb
            params = {
                keyPrefix+'user': self.options.tempdb_user if self.options.tempdb_user else self.options.mysqluser,
                keyPrefix+'passwd': self.options.tempdb_passwd if self.options.tempdb_passwd else '',
                keyPrefix+'host': self.options.tempdb_host if self.options.tempdb_host else self.options.host,
                keyPrefix+'port': self.options.tempdb_port if self.options.tempdb_port else self.options.port,
                keyPrefix+'socket': '',
                keyPrefix+'db': self.options.tempdb_name,
            }
            if params[keyPrefix+'host'] == 'localhost':
                if self.options.tempdb_socket is None:
                    if getattr(self.options, 'mysqlsocket', None) and self.options.mysqlsocket != 'None':
                        params[keyPrefix+'socket'] = self.options.mysqlsocket
                else:
                        params[keyPrefix+'socket'] = self.options.tempdb_socket
        else:
            # create the tempdb
            params = {
                keyPrefix+'user': self.options.mysqluser,
                keyPrefix+'passwd': self.options.mysqlpasswd if self.options.mysqlpasswd else '',
                keyPrefix+'host': self.options.host,
                keyPrefix+'port': self.options.port,
                keyPrefix+'socket': '',
                keyPrefix+'db': self.options.mysqldb,
            }
            if params[keyPrefix+'host'] == 'localhost':
                if self.options.tempdb_socket is None:
                    if getattr(self.options, 'mysqlsocket', None) and self.options.mysqlsocket != 'None':
                        params[keyPrefix+'socket'] = self.options.mysqlsocket
                else:
                        params[keyPrefix+'socket'] = self.options.tempdb_socket
        return params
        
def backup_zodb(path, user, passwd, db, port, socket=None):
    # back up existing datatabase with db command line client
    return "/tmp/zodb.sql.gz"


def getRelstorageConnection(
        host='localhost',
        port=3306,
        user='root',
        passwd=None,
        db='zodb',
        socket=None,
        keep_history=False):

    from relstorage.storage import RelStorage
    from relstorage.adapters.mysql import MySQLAdapter
    connectionParams = {
        'host' : host,
        'port' : port,
        'user' : user,
        'passwd' : passwd,
        'db' : db,
    }
    if socket:
        connectionParams['unix_socket'] = socket
    kwargs = {
        'keep_history': keep_history,
    }
    from relstorage.options import Options
    adapter = MySQLAdapter(options=Options(**kwargs),**connectionParams)
    storage = RelStorage(adapter, **kwargs)
    from ZODB import DB
    db = DB(storage, 0)
    return db


if __name__ == '__main__':
    upgradeManager = UpgradeManager()
    
    upgradeManager.run()

