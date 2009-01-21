#! /usr/bin/env python
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__="""diagnostic

Gather basic details on an installation into a single zip file for
reporting to Zenoss support.

"""
# It is important that this file produce few warnings/problems on a
# standard box, and makes as few assumptions as possible about things
# that should work.

import getopt
import glob
import logging
import os
import subprocess
import sys
import tempfile
import time
import zipfile


# Yucky global
fd, mysqlcreds = tempfile.mkstemp()

archive_name = time.strftime("diagnostic-%Y-%m-%d-%H-%M.zip")
archive = zipfile.ZipFile(archive_name, 'w', compression=zipfile.ZIP_DEFLATED)

zenhome = ''

# try to guess at the usual locations
for location in [os.environ.get('ZENHOME', '/not there'),
                 '/opt/zenoss',
                 '/home/zenoss',
                 '/usr/local/zenoss']:
    if os.path.exists(os.path.join(location, 'bin/zenoss')):
        zenhome = location
        break

# files to put into the zip file
files = [
    # name, file
    ('my.cnf', '/etc/mysql/my.cnf'),
    ('my.cnf', '$ZENHOME/mysql/my.cnf'),
    ('ZVersion', '$ZENHOME/Products/ZenModel/ZVersion.py'),
    ('etc', '$ZENHOME/etc'),
    ('log', '$ZENHOME/log'),
    ('distro-deb', '/etc/debian_version'),
    ('distro-rh', '/etc/redhat-release'),
    ('distro-fed', '/etc/fedora-release'),
    ('distro-suse', '/etc/SuSE-release'),
    ('distro-conary', '/etc/distro-release'),
]

# commands to run to get information about resources, the os, etc.
commands = [ 
    # name, program args
    ('df', ('df', '-a')),
    ('top', ('top', '-b', '-n', '3', '-c')),
    ('vmstat', ('vmstat', '1', '3')),
    ('free', ('free',)),
    ('zenpack', ('zenpack', '--list')),
    ('pspython', ('ps', '-C', 'python', '-F')),
    ('psjava', ('ps', '-C', 'java', '-F')),
    ('uname', ('uname', '-a')),
    ('uptime', ('uptime')),
    ('zenoss', ('zenoss', 'status')),
    ('mysqlstats', ('mysql', '--defaults-file=%s' % mysqlcreds,
                    '-e', 'show status')),
    ('heartbeats', ('mysql', '--defaults-file=%s' % mysqlcreds,
                    '-e', 'select * from heartbeat')),
    ('eventCount', ('mysql', '--defaults-file=%s' % mysqlcreds,
                    '-e', 'select count(*) from status')),
    ('historyCount', ('mysql', '--defaults-file=%s' % mysqlcreds,
                      '-e', 'select count(*) from history')),
    ('mysqlstatus', ('mysql', '--defaults-file=%s' % mysqlcreds,
                    '-e', 'select * from status')),
    ('crontab', ('crontab', '-l')),
    ('patches', ('sh', '-c', 'ls -l $ZENHOME/Products/*.patch')),
    ('javaVersion', ('/usr/bin/env', 'java', '-version')),
    ('zenpacks', ('ls', '-l', '$ZENHOME/ZenPacks')),
    ('ifconfig', ('ifconfig', '-a')),
]
# These commands only work if you are root
root_commands = [
    # name, program args
    ('iptables', ('iptables', '-L')),
    ('crontab', ('crontab', '-u', 'root', '-l')),
]

def zenhubConnections():
    "Scan the netstat connection information to see who is connected to zenhub"
    pids = os.popen('pgrep -f zenhub.py').read().split()
    lines = os.popen('netstat -anp 2>/dev/null').read().split('\n')
    result = lines[0:2]
    for line in lines[2:]:
        for pid in pids:
            if line.find(pid) >= 0:
                result.append(line)
                break
    return '\n'.join(result)

def mysqlfiles():
    "pull in the mysql files if you can find them and read them"
    for path in '/var/lib/mysql/events', '$ZENHOME/../mysql/data/events':
        try:
            os.listdir(path)
            return os.popen('ls -l %s' % path).read()
        except OSError, ex:             # permission denied
            pass
    return ''

def zenossInfo():
    "get the About:Versions page data"
    try:
        import Globals
        from Products.ZenUtils.ZenScriptBase import ZenScriptBase
        zsb = ZenScriptBase(noopts=True, connect=True)
        zsb.getDataRoot()
        result = []
        for record in zsb.dmd.About.getAllVersions():
            result.append('%10s: %s' % (record['header'], record['data']))
        result.append('%10s: %s' % ('uuid', zsb.dmd.uuid))
        return '\n'.join(result)
    except Exception, ex:
        log.exception(ex)

# the python functions we'll call
functions = [
    # name, python function, args
    ('hubConn', zenhubConnections, (), {}),
    ('mysqlfiles', mysqlfiles, (), {}),
    ('zenossInfo', zenossInfo, (), {}),
    ]


def getmysqlcreds():
    """Fetch the mysql creds from the object database and store them
    in the global file for use in later commands.

    returns True on success, False on failure
    """
    pids = os.popen('pgrep -f zeo').read().split('\n')
    pids = [int(p) for p in pids if p]
    if len(pids) < 3:
        log.warning('zeo is not running')
        return False
    log.debug("Fetching mysql credentials")
    mysqlpass = 'zenoss'
    mysqluser = 'zenoss'
    mysqlport = '3306'
    mysqlhost = 'localhost'
    sys.path.insert(0, os.path.join(zenhome, 'lib/python'))
    try:
        import Globals
        from Products.ZenUtils.ZenScriptBase import ZenScriptBase
        zsb = ZenScriptBase(noopts=True, connect=True)
        zsb.getDataRoot()
        dmd = zsb.dmd
        mysqlpass = dmd.ZenEventManager.password
        mysqluser = dmd.ZenEventManager.username
        mysqlport = dmd.ZenEventManager.port
        mysqlhost = dmd.ZenEventManager.host
    except Exception, ex:
        log.exception("Unable to open the object database for "
                      "mysql credentials")
    os.write(fd, '''[client]
password=%s
user=%s
port=%s
host=%s
database=events
''' % (mysqlpass, mysqluser, mysqlport, mysqlhost) )
    os.close(fd)
    return True

def archiveText(name, output):
    "if the output is interesting, put it into the archive"
    if output:
        zi = zipfile.ZipInfo(name)
        # default perms for writestr are ---------, not -rw--------
        zi.external_attr = 0600 << 16L
        # default creation date is not today, but 1980.
        zi.date_time = time.localtime(time.time())[:6]
        archive.writestr(zi, output)

def process_functions(functions, skip):
    "Call arbitrary python code to extract data"
    for name, function, args, kw in functions:
        if name in skip: continue
        try:
            output = function(*args, **kw)
            archiveText('diagnostic/%s.txt' % name, output)
        except Exception, ex:
            log.exception("function %s failed", name)

def process_commands(commands, skip):
    "Run some commands and put the result into the archive file"
    for name, program_args in commands:
        if name in skip:
            log.info("Skipping %s", name)
            continue
        try:
            log.info("Running %s", name)
            fp = subprocess.Popen(program_args,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
            output, error = fp.communicate()
            if error:
                log.info("%s command had an error: %s", name, error)
            code = fp.wait()
            if code != 0:
                log.info("%s command returned code %d", name, code)
                if not output:
                    output = "Error occured, exit code %d\n%s" % (code, error)
            archiveText('diagnostic/%s.txt' % name, output)
            log.debug("Output for %s:\n%s", name, output)
        except Exception, err:
            log.exception("%s command failed", name)

def process_files(files, skip):
    "Archive some key files"
    for name, filestr in files:
        if name in skip:
            log.info("Skipping %s", name)
            continue
        filename = filestr.replace('$ZENHOME', zenhome)
        filenames = []
        if os.path.isdir(filename):
            basename = os.path.sep.join(filename.split(os.path.sep)[:-1])
            for d, ds, fs in os.walk(filename):
                for f in fs:
                    fullname = os.path.join(d, f)
                    zipname = fullname[len(basename):].lstrip('/')
                    filenames.append((fullname, zipname))
        else:
            filenames.append((filename, filename.split(os.path.sep)[-1]))
        for filename, zipname in filenames:
            if os.path.exists(filename) and os.path.isfile(filename):
                try:
                    archive.write(filename, 'diagnostic/files/%s' % zipname)
                except Exception, ex:
                    log.exception("could not access %s", filestr)

def performance_graphs():
    "Turn the collector performance data into graphs and send them back"
    pattern = os.path.sep.join([zenhome, 'perf', 'Daemons', '*', '*.rrd'])
    for filename in glob.glob(pattern):
        try:
            parts = filename.split(os.path.sep)
            point = parts[-1][:-4]
            collector = parts[-2]
            graphName = '%s_%s.png' % (collector, point)
            subprocess.call(('rrdtool',
                             'graph',
                             graphName,
                             'DEF:ds0=%s:ds0:AVERAGE' % filename,
                             'LINE1:ds0'),
                            stdout=subprocess.PIPE)
            archive.write(graphName, 'diagnostic/Daemons/%s/%s.png' % (collector,
                                                                       point))
            os.unlink(graphName)
        except Exception, ex:
            log.exception("Exception generating an RRD Graph for %s" % filename)

def usage():
    print >>sys.stderr, """
Usage:
  $ZENHOME/bin/python diagnostic.py [-v] [-s] [-h $ZENHOME]
        -v         print in verbose messages about collection
        -s         suppress collection of some data (eg. -s Data.fs)
        -h         set ZENHOME explicity, useful when running the script as root
    """

def main():
    "Parse args and create a .zip file with the results"
    global log, zenhome, mysqlcreds
    try:
        if sys.platform.find('linux') < 0:
            print >>sys.stderr, "This script has not been ported to non-linux systems."
            return

        level = logging.WARNING
        skip = set()
        opts, ignored = getopt.getopt(sys.argv[1:], 's:vh:d?')
        for opt, value in opts:
            if   opt == '-s':
                skip.add(value)
            elif opt == '-d':
                files.append( ('Data.fs', '$ZENHOME/var/Data.fs') )
            elif opt == '-h':
                zenhome = value
            elif opt == '-v':
                level = logging.DEBUG
            else:
                os.unlink(archive_name)
                usage()
                return
        logging.basicConfig(level=level)
        log = logging.getLogger("diagnostic")
        os.environ['ZENHOME'] = zenhome
        os.environ['PATH'] += ":%s/bin" % zenhome
        if not getmysqlcreds():
            skip = skip.union(['zenpack',
                               'mysqlstats',
                               'heartbeats',
                               'mysqlstatus',
                               'zenossInfo'])

        if 'Daemons' not in skip:
            performance_graphs()
        process_functions(functions, skip)
        process_files(files, skip)
        process_commands(commands, skip)
        if os.getuid() == 0:
            process_commands(root_commands, skip)
        else:
            log.warning("Not running as root, ignoring commands that "
                        "require additional privileges")
        archive.close()
        print "Diagnostic data stored in %s" % archive_name
    finally:
        os.unlink(mysqlcreds)

main()
