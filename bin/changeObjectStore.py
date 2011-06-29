#!/usr/bin/env python
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import os
import re
import sys
import itertools
from subprocess import Popen, PIPE, call
from tempfile import mkstemp
import MySQLdb
import optparse
from _mysql_exceptions import OperationalError

def zenPath(*args):
    return os.path.abspath(os.path.join(os.environ['ZENHOME'], *args))


# Config files for all Zope clients need to be converted.
zopeClients = (
    'ZenActions', 'ZenBackup', 'ZenRestore', 'ZenHub', 'ZenJobs', 'ZenMib',
    'ZenMigrate', 'ZenPack',
    )

parser = optparse.OptionParser()


def main():
    if 'ZENHOME' not in os.environ:
        print >> sys.stderr, (
            "ZENHOME not set. You must run this script as the zenoss user.")
        sys.exit(1)

    if getZopeStore() == 'mysql':
        print >> sys.stderr, "You're already using the mysql objectstore."
        sys.exit(1)

    print "Converting object store from ZEO to MySQL..."
    convertFromZeoToMySql()


def getZopeStore():
    zope_conf = open(zenPath('etc', 'zope.conf'), 'r')
    in_zodb_main = False
    for line in zope_conf:
        if line.strip().startswith('#'): continue
        elif "<zodb_db main>" in line: in_zodb_main = True
        if in_zodb_main:
            if "</zodb_db>" in line:
                in_zodb_main = False
            elif "<zeoclient>" in line:
                return "zeo"
            elif "<mysql>" in line:
                return "mysql"

    zope_conf.close()


def findDataFs():
    zenhome = os.environ['ZENHOME']
    zeo_conf = open(zenPath('etc', 'zeo.conf'), 'r')
    instance = zenhome
    in_filestorage = False
    for line in zeo_conf:
        if line.startswith('#'): continue
        if '%define INSTANCE' in line:
            instance = line.strip().split(' ')[-1]
        elif '<filestorage 1>' in line:
            in_filestorage = True
        if in_filestorage:
            if '</filestorage>' in line:
                in_filestorage = False
            elif 'path' in line:
                return line.strip().split(' ')[-1].replace(
                    '$INSTANCE', instance)


def getMySqlSettings():
    o, args = parser.parse_args(args=sys.argv[1:])
    return o.host, o.port, o.db, o.user, o.passwd, o.rootpw


def createMySqlDatabase(host, port, db, user, passwd, root):
    conn = None
    queries = (
        'DROP DATABASE IF EXISTS %s;' % db,
        'CREATE DATABASE %s;' % db,
        "GRANT ALL ON %s.* TO %s@'%s' IDENTIFIED BY '%s';" % (db, user, host,
                                                              passwd),
        "GRANT ALL ON %s.* TO %s@'%%' IDENTIFIED BY '%s';" % (db, user,
                                                              passwd),
        "FLUSH PRIVILEGES;"
    )
    try:
        args = dict(host=host, port=port, user='root')
        if root: args['passwd'] = root
        conn = MySQLdb.connect(**args)
        curs = conn.cursor()
        curs._defer_warnings = True
        for q in queries:
            curs.execute(q)
            unused = curs.fetchall()
    except OperationalError, ex:
        if 'Lost connection to MySQL server during query' in ex[1]:
            pass
        else:
            raise
    finally:
        if conn is not None: conn.close()


def updateConf(conf, toAdd=[], toRemove=[]):
    filename = zenPath('etc', '%s.conf' % conf)
    new_contents = []

    try:
        conf_file = open(filename, 'r')
        for line in conf_file:
            found_match = False
            for option in toRemove + [ x for x, y in toAdd ]:
                if re.match(r'^%s\s+\S+' % option, line):
                    found_match = True

            if not found_match:
                new_contents.append(line)

        conf_file.close()
    except IOError:
        # We'll create the config file if it doesn't exist.
        pass

    for option, value in toAdd:
        new_contents.append('%s %s\n' % (option, value))

    conf_file = open(filename, 'w')
    for line in new_contents:
        conf_file.write(line)

    conf_file.close()
    return '%s - UPDATED' % filename


def convertFromZeoToMySql():
    host, port, db, user, passwd, root = getMySqlSettings()

    print "Creating database..."
    print "-"*79
    createMySqlDatabase(host, port, db, user, passwd, root)
    print "%s database created successfully." % db
    print

    fd, fn = mkstemp()
    zodbconvert_conf = os.fdopen(fd, 'w')
    zodbconvert_conf.write('<filestorage source>\n')
    zodbconvert_conf.write('  path %s\n' % findDataFs())
    zodbconvert_conf.write('</filestorage>\n\n')

    zodbconvert_conf.write('<relstorage destination>\n')
    zodbconvert_conf.write('  <mysql>\n')
    zodbconvert_conf.write('    host %s\n' % host)
    zodbconvert_conf.write('    port %s\n' % port)
    zodbconvert_conf.write('    db %s\n' % db)
    zodbconvert_conf.write('    user %s\n' % user)
    zodbconvert_conf.write('    passwd %s\n' % passwd)
    zodbconvert_conf.write('  </mysql>\n')
    zodbconvert_conf.write('</relstorage>\n')
    zodbconvert_conf.close()

    print "Shutting down ZEO for the last time..."
    print "-"*79
    try:
        call([zenPath("bin", "zeoctl"), "stop"])
    except OSError:
        pass
    print

    print "Analyzing ZODB..."
    print "-"*79
    p = Popen([zenPath("bin", "python"), zenPath("bin", "zodbconvert"), "--dry-run", fn], stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    totaltxs = int(stdout.splitlines()[-1].split()[2])
    print "%d transactions to be copied." % totaltxs
    print

    # Monkeypatch in order to get a running count of transactions copied
    counter = itertools.count()
    counter.next()
    from relstorage.storage import RelStorage
    old_tpc_finish = RelStorage.tpc_finish
    def new_tpc_finish(*args, **kwargs):
        txnum = counter.next()
        sys.stdout.write('\r  -  Copying transaction %d of %d' % (txnum, totaltxs))
        sys.stdout.flush()
        if txnum==totaltxs:
            print
        return old_tpc_finish(*args, **kwargs)
    RelStorage.tpc_finish = new_tpc_finish

    print "Loading current ZODB into MySQL. This may take some time..."
    print "-"*79
    from relstorage import zodbconvert
    zodbconvert.main([None, '--clear', fn], _print_sane_output)
    os.unlink(fn)
    print

    # Undo the monkeypatch
    RelStorage.tpc_finish = old_tpc_finish

    print "Removing ZEO from startup script..."
    print "-"*79
    removeZeoctlFromStartup()
    print "Done."
    print

    print "Converting Zenoss configuration files.."
    print "-"*79
    print "Zope (%s)" % convertZopeConfToMySql(host, db, user, passwd)
    print

    for proc in zopeClients:
        print "%s (%s)" % (proc, updateConf(proc.lower(), toRemove=[
            'host', 'port', 'mysqldb', 'mysqluser', 'mysqlpasswd']))

    print "Global (%s)" % updateConf('global', toAdd=[
        ('host', host), ('port', port), ('mysqldb', db), ('mysqluser', user),
        ('mysqlpasswd', passwd)])


def convertZopeConfToMySql(host, db, user, passwd):
    zc = zenPath('etc', 'zope.conf')
    zcf = open(zc, 'r')
    zeoclient = False
    nc = []
    for line in zcf:
        meaning = re.sub('^\s+', '', line.strip())
        if meaning.startswith('<zeoclient>'):
            zeoclient = True
        if not zeoclient:
            nc.append(line)
        if zeoclient and meaning.startswith('</zeoclient>'):
            zeoclient = False
            nc.append('  %import relstorage\n')
            nc.append('  <relstorage>\n')
            nc.append('    # Uncomment these to use memcached\n')
            nc.append('    # cache-servers 127.0.0.1:11211\n')
            nc.append('    # cache-module-name memcache\n')
            nc.append('    <mysql>\n')
            nc.append('      host %s\n' % host)
            nc.append('      db %s\n' % db)
            nc.append('      user %s\n' % user)
            nc.append('      passwd %s\n' % passwd)
            nc.append('    </mysql>\n')
            nc.append('  </relstorage>\n')
    zcf.close()
    with open(zc, 'w') as zcf:
        for line in nc:
            zcf.write(line)
    return '%s - UPDATED' % zc


def removeZeoctlFromStartup():
    # Clean up zenoss init script
    l = []
    fname = zenPath('bin', 'zenoss')
    with open(fname, 'r') as f:
        for line in f:
            if 'C="$C zeoctl"' not in line:
                l.append(line)
    with open(fname, 'w') as f:
        for line in l:
            f.write(line)
    # Clean up daemons.txt
    l = []
    fname = zenPath('etc', 'daemons.txt')
    try:
        with open(fname, 'r') as f:
            for line in f:
                if 'zeoctl' not in line:
                    l.append(line)
        with open(fname, 'w') as f:
            for line in l:
                f.write(line)
    except IOError:
        pass


def _print_sane_output(msg):
    if 'description' not in msg:
        sys.stdout.write(msg)


if __name__ == '__main__':
    parser.add_option('--host',
           dest="host",default="localhost",
           help="hostname of MySQL object store")
    parser.add_option('--port',
           dest="port", type="int", default=3306,
           help="port of MySQL object store")
    parser.add_option('--user', dest='user', default='zenoss',
           help='username for MySQL object store')
    parser.add_option('--passwd', dest='passwd', default='zenoss',
           help='passwd for MySQL object store')
    parser.add_option('--db', dest='db', default='zodb',
           help='Name of database for MySQL object store')
    parser.add_option('--rootpw', dest='rootpw',
                help='MySQL root password')
    main()
