##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import yaml


# Lists out each modeler plugin and a list of which deviceProperties it specifies.
PARSER_PLUGIN_YAML = "/opt/zenoss/etc/nub/system/parserplugins.yaml"

def load_yaml():
    return yaml.load(file(PARSER_PLUGIN_YAML, 'r'))
