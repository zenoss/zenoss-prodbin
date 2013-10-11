#! /usr/bin/env python
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """zendiag

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
import datetime
import zipfile


# Yucky global
fd, mysqlcreds = tempfile.mkstemp()

archive_name = time.strftime("zendiag-%Y-%m-%d-%H-%M.zip")
archive = zipfile.ZipFile(archive_name, 'w', compression=zipfile.ZIP_DEFLATED)

zenhome = ''

# try to guess at the usual locations
for location in [os.environ.get('ZENHOME', '/not there'),
                 '/opt/zenoss',
                 '/home/zenoss',
                 '/usr/local/zenoss']:
    if os.path.exists(os.path.join(location, 'bin/zenoss')):
        zenhome = location
        sys.path.insert(0, zenhome)
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
    ('lsZENHOME', ('ls', '-laR', zenhome)),
    ('df', ('df', '-a')),
    ('top', ('top', '-b', '-n', '3', '-c')),
    ('vmstat', ('vmstat', '1', '3')),
    ('free', ('free',)),
    ('zenpack', ('zenpack', '--list')),
    ('pspython', ('ps', '-C', 'python', '-F')),
    ('psjava', ('ps', '-C', 'java', '-F')),
    ('uname', ('uname', '-a')),
    ('uptime', ('uptime',)),
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
    ('mysqladmin status', ('mysqladmin', '-uroot', 'status')),
    ('mysqladmin variables', ('mysqladmin', '-uroot', 'variables')),
    ('crontab', ('crontab', '-l')),
    ('patches', ('sh', '-c', 'ls -l %s/Products/*.patch' % zenhome)),
    ('javaVersion', ('/usr/bin/env', 'java', '-version')),
    ('zenpacks', ('ls', '-l', '%s/ZenPacks' % zenhome)),
    ('ifconfig', ('/sbin/ifconfig', '-a')),
]
# These commands only work if you are root
root_commands = [
    # name, program args
    ('iptables', ('iptables', '-L')),
    ('crontab', ('crontab', '-u', 'root', '-l')),
]


def zenhubConnections():
    "Scan the netstat connection information to see who is connected to zenhub"
    print "Scanning for zenhub connections..."
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

    def format_data(fmt, data):
        return [fmt % datum for datum in data] + ['']

    try:
        print "Gathering info from zodb..."
        import Globals
        from Products.ZenUtils.ZenScriptBase import ZenScriptBase
        from Products.Zuul import getFacade
        zsb = ZenScriptBase(noopts=True, connect=True)
        zsb.getDataRoot()

        header_data = [
            ('Report Data', datetime.datetime.now()),
            ('Server Key', zsb.dmd.uuid),
            ('Google Key', zsb.dmd.geomapapikey)]

        counter = {}
        decomm = 0
        for d in zsb.dmd.Devices.getSubDevices():
            if d.productionState < 0:
                decomm += 1
            else:
                index = '%s %s' % \
                    (d.getDeviceClassPath(), d.getProductionStateString())
                count = counter.get(index, 0)
                counter[index] = count + 1

        totaldev = zsb.dmd.Devices.countDevices()

        device_summary_header_data = [
            ('Total Devices', totaldev),
            ('Total Decommissioned Devices', decomm),
            ('Total Monitored Devices', totaldev - decomm),
        ]

        device_summary_header = ['Device Breakdown by Class and State:']

        counter_keylist = counter.keys()
        counter_keylist.sort()
        device_summary_data = [(k, counter[k]) for k in counter_keylist]

        zenpacks_header = ['ZenPacks:']
        zenpack_ids = zsb.dmd.ZenPackManager.packs.objectIds()

        zenoss_versions_data = [
            (record['header'], record['data']) for
                record in zsb.dmd.About.getAllVersions()]

        uuid_data = [('uuid', zsb.dmd.uuid)]

        event_start = time.time() - 24 * 60 * 60

        product_count=0
        for name in zsb.dmd.Manufacturers.getManufacturerNames():
            for product_name in zsb.dmd.Manufacturers.getProductNames(name):
                product_count = product_count + 1 

        # Hub collector Data
        collector_header = ['Hub and Collector Information']
        hub_data = []
        remote_count = 0
        local_count = 0 
        for hub in zsb.dmd.Monitors.Hub.getHubs():
            hub_data.append("Hub: %s" % hub.id)
            for collector in hub.collectors():
                    hub_data.append("\tCollector: %s IsLocal(): %s" % (collector.id,collector.isLocalHost()))
                    if not collector.isLocalHost():
                        hub_data.append("\tCollector(Remote): %s" % collector.id)
                        remote_count = remote_count + 1
                    else:
                        hub_data.append("\tCollector(Local): %s " % collector.id)
                        local_count = local_count + 1

        zep = getFacade('zep')
        tail_data = [
            ('Evt Rules', zsb.dmd.Events.countInstances()),
            ('Evt Count (Last 24 Hours)', zep.countEventsSince(event_start)),
            ('Reports', zsb.dmd.Reports.countReports()),
            ('Templates', zsb.dmd.Devices.rrdTemplates.countObjects()),
            ('Systems', zsb.dmd.Systems.countChildren()),
            ('Groups', zsb.dmd.Groups.countChildren()),
            ('Locations', zsb.dmd.Locations.countChildren()),
            ('Users', len(zsb.dmd.ZenUsers.getUsers())),
            ('Product Count', product_count),
            ('Local Collector Count', local_count),
            ('Remote Collector Count', remote_count)]

        detail_prefix = '    '
        std_key_data_fmt = '%s: %s'
        detail_std_key_data_fmt = detail_prefix + std_key_data_fmt
        detail_data_fmt = detail_prefix + '%s'
        center_justify_fmt = '%10s: %s'

        return_data = (
            format_data(std_key_data_fmt, header_data) +
            format_data(std_key_data_fmt, device_summary_header_data) +
            device_summary_header +
            format_data(detail_std_key_data_fmt, device_summary_data) +
            zenpacks_header +
            format_data(detail_data_fmt, zenpack_ids) +
            format_data(center_justify_fmt, zenoss_versions_data + uuid_data) +
            collector_header +
            format_data('%s', hub_data) +
            format_data(std_key_data_fmt, tail_data))

        return '\n'.join(return_data)

    except Exception, ex:
        log.exception(ex)

def md5s():
    "Calculate the md5sums of all files in zenhome"
    from os import listdir, sep
    from os.path import isdir,isfile
    try:
        # python 2.6+ version
        import hashlib as md5
    except Exception, ex:
        # python 2.4 version
        import md5
        md5.md5 = md5.new

    def sumfile(fobj):
        '''Returns an md5 hash for an object with read() method.'''
        m = md5.md5()
        while True:
            d = fobj.read(8096)
            if not d:
                break
            m.update(d)
        return m.hexdigest()

    def walk(dir,prefix='',results=[]):
        if prefix == '':
            prefix = dir
            if not prefix.endswith(sep):
                prefix = prefix + sep
        for fileobj in listdir(dir):
            path = dir + sep + fileobj
            if isdir(path):
                ignoredirs = [ 'backups','doc','skel','perf','log' ]
                if fileobj in ignoredirs: continue
                walk(path,prefix=prefix,results=results)
            elif isfile(path):
                ignoreFiletypes = [ 'pyc','pyo','rrd' ]
                if fileobj.rsplit('.',1)[-1] in ignoreFiletypes: continue
                try:
                    f = file(path,'rb')
                    results.append("%s %s" % ( sumfile(f), path[len(prefix):]))
                except:
                    log.warning('Unable to access %s for md5' % path)
        return results

    return '\n'.join(walk(zenhome))

# the python functions we'll call
functions = [
    # name, python function, args
    ('hubConn', zenhubConnections, (), {}),
    ('mysqlfiles', mysqlfiles, (), {}),
    ('zenossInfo', zenossInfo, (), {}),
    ('md5s', md5s, (), {}),
    ]


def getmysqlcreds():
    """Fetch the mysql creds from the object database and store them
    in the global file for use in later commands.

    returns True on success, False on failure
    """
    pids = os.popen('pgrep -f zeo.py').read().split('\n')
    pids = [int(p) for p in pids if p]
    if len(pids) < 1:
        log.warning('zeo is not running')
        return False
    log.debug("Fetching mysql credentials")
    print "Fetching mysql credentials"
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
        pass
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
            print "Gathering info for function %s" % name
            output = function(*args, **kw)
            archiveText('zendiag/%s.txt' % name, output)
        except Exception, ex:
            log.exception("function %s failed", name)


def process_commands(commands, skip):
    "Run some commands and put the result into the archive file"
    for name, program_args in commands:
        if name in skip:
            log.info("Skipping %s", name)
            continue
        try:
            log.debug("Running %s (%s)" % (name, " ".join(program_args)))
            print "Running %s (%s)" % (name, " ".join(program_args))
            fp = subprocess.Popen(program_args,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
            output, error = fp.communicate()
            code = fp.wait()
            if error:
                log.info("%s command had an error: %s", name, error)
            if code != 0:
                log.info("%s command returned code %d", name, code)
                if not output:
                    output = "Error occured, exit code %d\n%s" % (code, error)
            archiveText('zendiag/%s.txt' % name, output)
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
                    archive.write(filename, 'zendiag/files/%s' % zipname)
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
            archive.write(graphName, 'zendiag/Daemons/%s/%s.png' % (collector,
                                                                       point))
            os.unlink(graphName)
        except Exception, ex:
            log.exception("Exception generating an RRD Graph for %s" % filename)


def usage():
    print >>sys.stderr, """
Usage:
  $ZENHOME/bin/python zendiag.py [-v] [-s] [-h $ZENHOME]
        -v         print in verbose messages about collection
        -d         include the object database (Data.fs)
        -s         suppress collection of some data (eg. -s Daemons)
        -h         set ZENHOME explicity
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
        logging.basicConfig()
        log = logging.getLogger('zendiag')
        log.setLevel(level)
        log.info('Starting zendiag')

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
        #if os.getuid() == 0:
        #    process_commands(root_commands, skip)
        #else:
        #    log.warning("Not running as root, ignoring commands that "
        #                "require additional privileges")
        archive.close()
        print "Diagnostic data stored in %s" % archive_name
    finally:
        os.unlink(mysqlcreds)

if __name__ == '__main__':
    main()
