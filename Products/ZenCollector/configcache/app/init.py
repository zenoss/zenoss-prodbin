##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from OFS.Application import import_products
from Zope2.App import zcml

import Products.ZenWidgets

from Products.ZenUtils.Utils import load_config, load_config_override
from Products.ZenUtils.zenpackload import load_zenpacks


def initialize_environment(configs=(), overrides=()):
    import_products()
    load_zenpacks()
    zcml.load_site()
    load_config_override('scriptmessaging.zcml', Products.ZenWidgets)
    for filepath, module in configs:
        load_config(filepath, module)
    for filepath, module in overrides:
        load_config_override(filepath, module)
