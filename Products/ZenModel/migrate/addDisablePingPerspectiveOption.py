##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """
add --disable-ping-perspective option to daemons configuration files
"""

import logging
log = logging.getLogger("zen.migrate")

from Products.ZenUtils.Utils import zenPath
import Migrate
import yaml


class AddDisablePingPerspectiveOption(Migrate.Step):

    version = Migrate.Version(5, 2, 0)

    def conf_exist(self, conf_name):
        config_fullpath = zenPath("etc", conf_name)
        if os.path.exists(config_fullpath):
            return True
        return False


    def process_config(self, conf_name):
        config_fullpath = zenPath("etc", conf_name)
        update_string = """# Disable ping perspective, default: True
#disable-ping-perspective True
#

"""
        try:
            with open(config_fullpath, 'r') as fread:
                if 'disable-ping-perspective' not in fread.read():
                    fwrite = open(config_fullpath, 'a')
                    fwrite.write(update_string)
                    fwrite.close()
                    log.info("%s : Updated.", config_fullpath)
        except e:
            log.info("%s : Update failed.", config_fullpath)


    def cutover(self, dmd):
        configs_to_update = ['zencommand.conf',
                            'zenjmx.conf',
                            'zenmail.conf',
                            'zenmailtx.conf',
                            'zenmodeler.conf',
                            'zenperfsnmp.conf',
                            'zenping.conf',
                            'zenpop3.conf',
                            'zenprocess.conf',
                            'zenpropertymonitor.conf',
                            'zenpython.conf',
                            'zenstatus.conf',
                            'zensyslog.conf',
                            'zentrap.conf',
                            'zenucsevents.conf',
                            'zenvsphere.conf',
                            'zenwebtx.conf']

        log.info("Updating daemons configuration files with --disable-ping-perspective option.")

        for config in configs_to_update:
            if self.conf_exist(config):
                self.process_config(config)


AddDisablePingPerspectiveOption()
