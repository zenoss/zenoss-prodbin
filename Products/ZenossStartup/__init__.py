##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import json
import os.path
import logging

log = logging.getLogger("zen.ZenossStartup")

from zope.dottedname.resolve import resolve
from Products.CMFCore.utils import ProductsPath

from Products.ZenUtils.PkgResources import pkg_resources



# Iterate over all ZenPack eggs and load them
for zpkg  in pkg_resources.iter_entry_points('zenoss.zenpacks'):
    try:
        pkg_path = zpkg.load().__path__[0]
        if pkg_path not in ProductsPath:
            ProductsPath.insert(0, pkg_path)

        # Import the pack and tack it onto Products
        import Products

        module = resolve(zpkg.module_name)
        setattr(Products, zpkg.module_name, module)

    except Exception, e:
        # This messes up logging a bit, but if we need to report
        # an error, this saves hours of trying to find out what's going on
        logging.basicConfig()
        log.exception("Error encountered while processing %s",
                      zpkg.module_name)
