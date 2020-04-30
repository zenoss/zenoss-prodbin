##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import yaml

DATASOURCE_YAML = "/opt/zenoss/etc/nub/system/datasources.yaml"

def load_yaml():
    return yaml.load(file(DATASOURCE_YAML, 'r'))
