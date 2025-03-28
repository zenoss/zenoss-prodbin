##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import importlib
import os

from Products.ZenModel.migrate import Migrate


def main():
    _register_migration_scripts()
    Migrate.Migration().main()


def _register_migration_scripts():
    # NOTE: migration scripts are "registered" by importing them.
    for module in os.listdir(os.path.dirname(__file__)):
        if module == '__init__.py' or module[-3:] != '.py':
            continue
        importlib.import_module(
            "Products.ZenModel.migrate.{}".format(module[:-3])
        )
