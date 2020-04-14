##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import yaml


# This file is built by update_zenpacks.py and includes all of the zenpack-
# defined device classes, monitoring templates, etc.
ZENPACK_DEVICECLASS_YAML = "/opt/zenoss/etc/nub/system/zenpack_deviceclasses.yaml"

def load_yaml():
    return yaml.load(file(ZENPACK_DEVICECLASS_YAML, 'r'))
