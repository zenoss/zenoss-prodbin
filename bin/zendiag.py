#! /usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from argparse import ArgumentParser

import sys
import time
import datetime
import os
import zipfile
import logging
import subprocess
logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s')
log = logging.getLogger('zendiag')
log.setLevel(logging.INFO)

import Globals
from Products.ZenUtils.GlobalConfig import globalConfToDict
from Products.ZenUtils.Utils import supportBundlePath
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.Zuul import getFacade


__doc__ = """zendiag

Gather basic details on an installation into a single zip file for
reporting to Zenoss support.

This is expected to run as the zenoss user using Zenoss' python, and
designed to run on Zenoss 5.x, inside of Control Center.  Additionally,
$ZENHOME is assumed to be set.
"""

class ZenDiag(object):

    def __init__(self, zenhome):
        self.zenhome = zenhome
        self.archive = self.generate_bundle()
        self.zsb = ZenScriptBase(noopts=True, connect=True)

    def run_and_log_command(self, name, cmd):
        output=''
        try:
            log.debug('Running command %s', cmd)
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
            log.info('Successfully ran %s', name)
            self.archiveText('zendiag/{}.txt'.format(name), output)
        except subprocess.CalledProcessError as e:
            log.warn('Command failed:')
            log.exception(e)
            for line in output.splitlines():
                log.warn(line)


    def generate_bundle(self):
        """
        Generate and return an empty zipfile to archive everything to
        """
        archive_name = time.strftime("zendiag-%Y-%m-%d-%H-%M.zip")
        return zipfile.ZipFile(
            supportBundlePath(archive_name),
            'w',
            compression=zipfile.ZIP_DEFLATED
        )

    def archiveText(self, name, output):
        "if the output is interesting, put it into the archive"
        if output:
            zi = zipfile.ZipInfo(name)
            # default perms for writestr are ---------, not -rw--------
            zi.external_attr = 0600 << 16L
            # default creation date is not today, but 1980.
            zi.date_time = time.localtime(time.time())[:6]
            self.archive.writestr(zi, output)

    def get_database_info(self):
        def do_database_cmds(db, config):
            dbVals = {}
            dbParams = [ '{}-{}'.format(db, param) for param in ['host', 'port', 'db', 'user', 'password'] ]
            for option in dbParams:
                if not config.get(option, None):
                    log.warn('Missing parameter %s from config, skipping %s-related data', option, db)
                    return
                dbVals[option] = config.get(option)
            # commands to run
            cmds = {
                "mysql-status-{}".format(db): "mysqladmin -u{} -p{} -h {} extended-status".format(dbVals['{}-user'.format(db)], dbVals['{}-password'.format(db)], dbVals['{}-host'.format(db)]),
                "mysql-variables-{}".format(db): "mysqladmin -u{} -p{} -h {} variables".format(dbVals['{}-user'.format(db)], dbVals['{}-password'.format(db)], dbVals['{}-host'.format(db)])
            }
            # run the commands
            for name,cmd in cmds.iteritems():
                self.run_and_log_command(name, cmd)

        config = globalConfToDict()
        do_database_cmds('zodb', config)
        do_database_cmds('zep', config)

    def get_zep_info(self):
        try:
            log.info('Gathering zep stats info')
            zepfacade = getFacade('zep')
            statsList = zepfacade.getStats()
            self.archiveText('zendiag/event_stats.txt', '\n\n'.join([str(item) for item in statsList]))
        except Exception as ex:
            log.exception(ex)

    def get_zenoss_info(self):
        """
        Gather various peices of information about zenoss itself from inside a container
        """

        # 1) Get various things from zodb

        def format_data(fmt, data):
            return [fmt % datum for datum in data] + ['']

        try:
            log.info("Gathering info from zodb")
            header_data = [
                ('Report Data', datetime.datetime.now()),
                ('Server Key', self.zsb.dmd.uuid),
                ('Google Key', self.zsb.dmd.geomapapikey)]

            counter = {}
            decomm = 0
            for d in self.zsb.dmd.Devices.getSubDevices():
                if d.productionState < 0:
                    decomm += 1
                else:
                    index = '%s %s' % \
                        (d.getDeviceClassPath(), d.getProductionStateString())
                    count = counter.get(index, 0)
                    counter[index] = count + 1

            totaldev = self.zsb.dmd.Devices.countDevices()

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
            zenpack_ids = self.zsb.dmd.ZenPackManager.packs.objectIds()

            zenoss_versions_data = [
                (record['header'], record['data']) for
                    record in self.zsb.dmd.About.getAllVersions()]

            uuid_data = [('uuid', self.zsb.dmd.uuid)]

            event_start = time.time() - 24 * 60 * 60

            product_count=0
            for name in self.zsb.dmd.Manufacturers.getManufacturerNames():
                for product_name in self.zsb.dmd.Manufacturers.getProductNames(name):
                    product_count = product_count + 1

            # Hub collector Data
            collector_header = ['Hub and Collector Information']
            hub_data = []
            remote_count = 0
            local_count = 0
            for hub in self.zsb.dmd.Monitors.Hub.getHubs():
                hub_data.append("Hub: %s" % hub.id)
                for collector in hub.collectors():
                        hub_data.append("\tCollector: %s IsLocal(): %s" % (collector.id, collector.id == 'localhost'))
                        if not collector.id == 'localhost':
                            hub_data.append("\tCollector(Remote): %s" % collector.id)
                            remote_count = remote_count + 1
                        else:
                            hub_data.append("\tCollector(Local): %s " % collector.id)
                            local_count = local_count + 1

            zep = getFacade('zep')
            tail_data = [
                ('Evt Rules', self.zsb.dmd.Events.countInstances()),
                ('Evt Count (Last 24 Hours)', zep.countEventsSince(event_start)),
                ('Reports', self.zsb.dmd.Reports.countReports()),
                ('Templates', self.zsb.dmd.Devices.rrdTemplates.countObjects()),
                ('Systems', self.zsb.dmd.Systems.countChildren()),
                ('Groups', self.zsb.dmd.Groups.countChildren()),
                ('Locations', self.zsb.dmd.Locations.countChildren()),
                ('Users', len(self.zsb.dmd.ZenUsers.getUsers())),
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

            self.archiveText('zendiag/zenoss-info.txt', '\n'.join(return_data))

        except Exception, ex:
            log.exception(ex)

        # 2) Get a list of zenpacks
        log.info('Gathering list of zenpacks')
        self.run_and_log_command('zenpack-list', 'zenpack --list')


    def get_files(self):
        """
        Arbitrary files to grab
        """
        files = [
            # '/absolute/path/py',
            # '/file/or/directory,
            os.path.join(self.zenhome, 'Products/ZenModel/ZVersion.py'),
            os.path.join(self.zenhome, 'etc')
        ]

        for filename in files:
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
                        self.archive.write(filename, 'zendiag/files/%s' % zipname)
                    except Exception, ex:
                        log.exception("could not access %s", filename)


    def wrapup(self):
        self.archive.close()
        log.info('Diagnostic data stored to %s', self.archive.filename)

    def run(self, verbose=False):
        """
        Main method that gets invoked.  Call with parsed arguments.
        """
        if verbose:
            log.setLevel(logging.DEBUG)
        self.get_database_info()
        self.get_zep_info()
        self.get_zenoss_info()
        self.get_files()
        self.wrapup()


if __name__ == '__main__':
    parser = ArgumentParser(description='Gather diagnostic data about Zenoss')
    parser.add_argument('--verbose','-v', action='store_true',
                        help='Enable verbose logging')
    argz = parser.parse_args()

    if not os.getenv('ZENHOME'):
        log.error('$ZENHOME is not set, exiting')
        sys.exit(1)

    zd = ZenDiag(os.getenv('ZENHOME'))
    zd.run(argz.verbose)

