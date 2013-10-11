#!/usr/bin/env python
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os
import sys

if os.environ.get('ZENHOME', None) is None:
    print "\nThis script must be run as the zenoss user.\n"
    print "Please switch to the zenoss user before re-running:"
    print "e.g.,  su - zenoss\n"
    sys.exit(2)

import Globals
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from ZODB.POSException import StorageError
import os.path
import re
from tempfile import NamedTemporaryFile
import memcache

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

        self.parser.add_option('--dry-run',
                    dest="dryRun",default=False, action='store_true',
                    help="don't actually perform any actions")

    def run(self):
        self.bailIfZenossRunning()

        if self.relstorageIsHistoryFree():
            print "The currently configured relstorage instance is history-free."
            print "No conversion required."
            sys.exit(0)
            
        print "History-preserving relstorage is detected."
        self.backupDB()
        
        print "Copying current zodb to non-history preserving temp database"
        configFile = self.writeZodbConvertConfig()
        self.createTempDB()
        self.convertZodb(configFile)
        self.dropZodb()
        
        print "Restoring Production ZODB instance from temp db."
        self.restore()

        updateZopeConfig(self.options.dryRun)
        flushMemcache(self.options.dryRun)

        print "*"*60
        if self.options.dryRun:
             print "This was a dry run. No changes have been commited."
        else:
             print "The conversion to history-free zodb schema is complete!"
             print "Upgrade this Zenoss instance to 4.0.2."
             print 
        f = "%s/zodb_with_history.sql.gz" % self.options.zodb_backup_path
        files = 0
        if os.path.exists(f):
            print "The original history-preserving backup exists:"
            print "\t",f
            files = files + 1
        f = "%s/zodb_without_history.sql.gz" % self.options.zodb_backup_path
        if os.path.exists(f):
            print "The converted history-fee backup exists:"
            print "\t",f
            files = files + 1
        if files and not self.options.dryRun:
            print "Please delete after verifying the upgrade was successful."
        print "*"*60

    def bailIfZenossRunning(self):
        cmd = "zenoss status | grep pid="
        if self.options.dryRun:
            print "[bypassing] Check for zenoss status: %s" % cmd
            return
        print "Checking zenoss status: %s\n" % cmd
        r = os.system(cmd)
        if r == 0:
            print "\nOne or more Zenoss daemons appear to be running.\n"
            print "Please stop Zenoss before running this script to avoid updates to the ZODB:"
            print "e.g.,  zenoss stop\n"
            sys.exit(1)
    
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
        if not self.options.dryRun:
            execOrDie(cmd)

        # Remove temporary configuration file
        os.unlink(configFile)

    def restore(self):
        zodbTempFilename = "%s/zodb_without_history.sql.gz" % self.options.zodb_backup_path 
        cmd = 'mysqldump %s --quick --max-allowed-packet=64M | gzip > %s ' % (
            self.createClientConnectionString(tempDB=True),
            zodbTempFilename,
        )
        print "Dumping zodb_temp to disk: %s " % cmd
        if not self.options.dryRun:
            execOrDie(cmd)

        self.dropTempDB()

        cmd = 'gunzip %s -c | mysql %s --max-allowed-packet=64M ' % (
            zodbTempFilename,
            self.createClientConnectionString(tempDB=False),
        )
        print "Restoring zodb from zodb_temp: %s " % cmd
        if not self.options.dryRun:
            execOrDie(cmd)
            os.unlink(zodbTempFilename)

    def dropZodb(self):
        cmd = 'mysql %s -e "drop database if exists %s; create database %s "' % (
            self.createClientConnectionString(db='', tempDB=True),
            self.options.mysqldb,
            self.options.mysqldb,
        )
        print "Dropping production ZODB: %s " % cmd
        if not self.options.dryRun:
            execOrDie(cmd)
    
    def backupDB(self):
        destFilename = '%s/zodb_with_history.sql.gz' % self.options.zodb_backup_path
        if os.path.exists(destFilename):
            print "Backup file exists. Remove or move %r." % destFilename
            sys.exit(1)
        cmd = 'mysqldump --quick --max-allowed-packet=64M --add-drop-table %s | gzip > "%s"' % (
            self.createClientConnectionString(),
            destFilename,
        )
        print "Backing up current ZODB: %s " % cmd
        if not self.options.dryRun:
            execOrDie(cmd)
        
    def createTempDB(self):
        cmd = 'mysql %s -e "drop database if exists %s; create database %s "' % (
            self.createClientConnectionString(db='', tempDB=True),
            self.options.tempdb_name,
            self.options.tempdb_name,
        )
        print "Creating TempDB: %s " % cmd
        if not self.options.dryRun:
            execOrDie(cmd)

    def dropTempDB(self):
        cmd = 'mysql %s -e "drop database if exists %s"' % (
            self.createClientConnectionString(db='', tempDB=True),
            self.options.tempdb_name,
        )
        print "Dropping TempDB: %s " % cmd
        if not self.options.dryRun:
            execOrDie(cmd)

    def createClientConnectionString(self, db=None,tempDB=False):
        params = self.getConnectionParameters(tempDB=tempDB)
        if params['passwd']:
            params['passwd'] = '-p%s' % params['passwd']
        if params['socket']:
            params['socket'] = '--socket="%s"' % params['socket']
        if params['host'] != 'localhhost' :
            params['port'] = '--port=%s' % params['port']
        else:
            params['port'] = ''
        if db is not None:
            params['db'] = db
        cmdArgs = '--user="%(user)s" --host="%(host)s" %(db)s %(passwd)s %(socket)s %(port)s ' % params
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
        

def updateZopeConfig(dryRun):
    zopeConfFilename = os.environ['ZENHOME'] + "/etc/zope.conf"
    zopeConf = open(zopeConfFilename, 'r').read()
    if 'keep-history' not in zopeConf:
        backup = zopeConfFilename + ".history-preserving"
        print "backing up existing zope config to %s" % backup
        cmd = 'cp -f "%s" "%s"' % (zopeConfFilename, backup,)
        print cmd
        if not dryRun:
            execOrDie(cmd)
        else:
            return
        zopeConf = zopeConf.replace("<relstorage>","<relstorage>\n    keep-history false ")
        newZopeConf = open(zopeConfFilename, 'w')
        newZopeConf.write(zopeConf)
        newZopeConf.close()

def flushMemcache(dryRun):
    zopeConfFilename = os.environ['ZENHOME'] + "/etc/zope.conf"
    for line in open(zopeConfFilename, 'r'):
        sline = line.strip()
        if sline.startswith('cache-servers'):
            servers = sline.split()[1:]
            try:
                from pprint import pprint
                print "Flushing memcache servers: " 
                pprint(servers)
                c = memcache.Client(servers)
                if not dryRun:
                    c.flush_all()
            except Exception as ex:
                print "problem flushing cache server %r: %r" % (servers, ex)
    

def execOrDie(cmd):
    r = os.system(cmd)
    if r != 0:
        print "cmd returned %r : %r ", (r, cmd,)
        sys.exit(r)

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

    if os.environ.get('ZENHOME', None) is None:
        print "ZENHOME is not set. Run this script as the zenoss user."
        sys.exit(2)
    upgradeManager = UpgradeManager()
    if (len(upgradeManager.args) > 0 and upgradeManager.args[0] == 'run') or (upgradeManager.options.dryRun):
        upgradeManager.run()
    else:
        upgradeManager.parser.print_usage()
        print """        This script converts a RelStorage-based ZODB from a transaction history-preserving schema
        to a transaction history-free schema to mitigate the possibility of excessive file system
        space requirements during normal Zenoss operation.  Typically this applies to 4.0.0 and
        4.0.1 installs.

             run\t\tPerform the conversion. You can override default settings with options.
                \t\tSee --help
             --help\t\tPrint help.
             --dry-run\t\tDisplay actions without commiting changes.

        Please run the following (as the zenoss user) prior to executing this script:
             zenossdbpack\t[optional but recommended]
             zenoss stop

        IMPORTANT:    This script should be run with guidance from Zenoss Support.

        * Please ensure you have adequate diskspace under /tmp.
        * We recommend you backup your ZODB prior to running this script in the event
          something goes wrong and you want to restore it.
        * This script should be run from the Zenoss master as the zenoss user.
        """
