#! /usr/bin/env python
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, 2009, 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
import optparse
import os
import subprocess
import sys
import copy

from config import ConfigFile

logging.basicConfig()
log = logging.getLogger("zen.zendb")

class ZenDBError(Exception):
    def __init__(self, msg=None):
        self.msg = msg
    def __str__(self):
        return repr('ZenDBError: %s' % self.msg)

class ZenDB(object):
    requiredParams = ('db-type', 'host', 'port', 'db', 'user')
    
    def __init__(self, useDefault, dsn={}, useAdmin=False):
        # parameter is muteable, use a local copy
        dsn = copy.deepcopy(dsn)
        self._db = useDefault 
        if useDefault in ('zep', 'zodb'):
            dbparams = self._getParamsFromGlobalConf(useDefault)
            for setting in dbparams:
                # only override the dsn settings not already specified
                if not dsn.get(setting):
                    if setting in ('user', 'password') and useAdmin:
                        # determine if global.conf specifies admin settings
                        key = 'admin-' + setting
                        if key in dbparams:
                            dsn[setting] = dbparams[key]
                    else:
                        dsn[setting] = dbparams[setting]
        
        # check to confirm we have all db params
        for setting in self.requiredParams:
            if not dsn.get(setting):
                raise ZenDBError('Missing a required DB connection setting '
                                 '(%s), and cannot continue. ' % setting)
        
        self.dbtype = dsn.pop('db-type')
        if self.dbtype not in ('mysql', 'postgresql'):
            raise ZenDBError('%s is not a valid database type.' % self.dbtype)
        log.debug('db type: %s' % self.dbtype)
        
        self.dbparams = dsn
        log.debug('connection params: %s' % str(self.dbparams))
    
    def _getParamsFromGlobalConf(self, defaultDb):
        zenhome = os.environ.get('ZENHOME')
        if not zenhome:
            raise ZenDBError('No $ZENHOME set. In order to use default '
                             'configurations, $ZENHOME must point to the '
                             'Zenoss install.')
        else:
            with open(os.path.join(zenhome, 'etc/global.conf'), 'r') as fp:
                globalConf = ConfigFile(fp)
                settings = {}
                for line in globalConf.parse():
                    if line.setting:
                        key, val = line.setting
                        if key.startswith(defaultDb + '-'):
                            key = key[len(defaultDb)+1:]
                            settings[key] = val
                return settings

    def getConnection(self, extraParams={}):
        if self.dbtype == 'mysql':
            from Products.ZenUtils.mysql import MySQLdb
            p = self.dbparams
            params = {}
            params['host'] = p['host']
            params['port'] = int(p['port'])
            params['user'] = p['user']
            params['passwd'] = p['password']
            params['db'] = p['db']
            if 'socket' in p:
                params['unix_socket'] = p['socket']
            elif self._db == 'zep':
                # ZEP does not use unix_socket, its a java app
                # assume the socket is the same as zodb's if the
                # hosts are the same
                zodbZenDB = ZenDB('zodb')
                if zodbZenDB.dbparams['host'] == params['host']:
                   if 'socket' in zodbZenDB.dbparams:
                       params['unix_socket'] = zodbZenDB.dbparams['socket']
            params.update(extraParams)
            connection = MySQLdb.connect(**params)
            return connection
        else:
            raise NotImplemented("This method does not support %s" % self.dbtype) 
    
    def dumpSql(self, outfile=None):
        # output to stdout if nothing passed in, open a file if a string is passed,
        # or use an open file if that's passed in
        if outfile is None:
            outfile = sys.stdout
        elif isinstance(outfile, basestring):
            outfile = open(outfile, 'w')
        if not isinstance(outfile, file):
            raise ZenDBError('SQL dump output file is invalid. If you passed in a '
                             'file name, please confirm that its location is '
                             'writable.')
        cmd = None
        env = os.environ.copy()
        if self.dbtype == 'mysql':
            # TODO: Handle compression of stream (--compress)?
            env['MYSQL_PWD'] = self.dbparams.get('password')
            cmd = ['mysqldump',
                   '--user=%s' % self.dbparams.get('user'),
                   '--host=%s' % self.dbparams.get('host'),
                   '--port=%s' % str(self.dbparams.get('port')),
                   '--single-transaction',
                   self.dbparams.get('db')]
        elif self.dbtype == 'postgresql':
            env['PGPASSWORD'] = self.dbparams.get('password')
            cmd = ['pg_dump',
                   '--username=%s' % self.dbparams.get('user'),
                   '--host=%s' % self.dbparams.get('host'),
                   '--port=%s' % self.dbparams.get('port'),
                   '--format=p',
                   '--no-privileges',
                   '--no-owner', 
                   '--create',
                   '--use-set-session-authorization',
                   self.dbparams.get('db')]
        if cmd:
            rc = subprocess.Popen(cmd, stdout=outfile, env=env).wait()
            if rc:
                raise subprocess.CalledProcessError(rc, cmd)
    
    def executeSql(self, sql=None):
        cmd = None
        env = os.environ.copy()
        if self.dbtype == 'mysql':
            env['MYSQL_PWD'] = self.dbparams.get('password')
            cmd = ['mysql',
                   '--batch',
                   '--skip-column-names',
                   '--user=%s' % self.dbparams.get('user'),
                   '--host=%s' % self.dbparams.get('host'),
                   '--port=%s' % str(self.dbparams.get('port')),
                   '--database=%s' % self.dbparams.get('db')]
        elif self.dbtype == 'postgresql':
            env['PGPASSWORD'] = self.dbparams.get('password')
            cmd = ['psql',
                   '--quiet',
                   '--tuples-only',
                   '--username=%s' % self.dbparams.get('user'),
                   '--host=%s' % self.dbparams.get('host'),
                   '--port=%s' % self.dbparams.get('port'),
                   self.dbparams.get('db')]
        if cmd:
            p = subprocess.Popen(cmd, env=env,
                                 stdin=subprocess.PIPE if sql else sys.stdin)
            try:
                if sql:
                    p.communicate(sql)
                rc = p.wait()
                if rc:
                    raise subprocess.CalledProcessError(rc, cmd)
            except KeyboardInterrupt:
                subprocess.call('stty sane', shell=True)
                p.kill()

if __name__ == '__main__':
    parser = optparse.OptionParser()
    
    # DB connection params
    parser.add_option('--usedb', dest='usedb', help='Use default connection settings (zodb/zep)')
    parser.add_option('--useadmin', action='store_true', dest='useadmin', help='Use Admin creds from --usedb')
    parser.add_option('--dbtype', dest='dbtype', help='Database Type')
    parser.add_option('--dbhost', dest='dbhost', help='Database Host')
    parser.add_option('--dbport', type='int', dest='dbport', help='Database Port')
    parser.add_option('--dbname', dest='dbname', help='Database Name')
    parser.add_option('--dbuser', dest='dbuser', help='Database User')
    parser.add_option('--dbpass', dest='dbpass', help='Database Password')
    
    # Usage options
    parser.add_option('--dump', action='store_true', dest='dumpdb', help='Dump database')
    parser.add_option('--dumpfile', dest='dumpfile', help='Output file for database dump (defaults to STDOUT)')
    parser.add_option('--execsql', dest='execsql', help='SQL to execute (defaults to STDIN)')
    
    # logging verbosity
    parser.add_option('-v', '--logseverity', default='INFO', dest='logseverity', help='Logging severity threshold')
    
    options, args = parser.parse_args()
    try:
        loglevel = int(options.logseverity)
    except ValueError:
        loglevel = getattr(logging, options.logseverity.upper(), logging.INFO)
    log.setLevel(loglevel)
    
    try:
        zdb = ZenDB(
            useDefault=options.usedb, 
            dsn = {
              'db-type': options.dbtype,
              'host': options.dbhost,
              'port': options.dbport,
              'db': options.dbname,
              'user': options.dbuser,
              'password': options.dbpass
            },
            useAdmin=options.useadmin,
        )
        
        if options.dumpdb:
            zdb.dumpSql(options.dumpfile)
        else:
            zdb.executeSql(options.execsql)
    except ZenDBError as e:
        log.error(e.msg)
        sys.exit(-1)
    except subprocess.CalledProcessError as e:
        log.error('Error executing command: %s' % repr(e.cmd))
        sys.exit(e.returncode)
