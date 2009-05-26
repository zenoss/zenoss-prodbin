######################################################################
#
# Copyright 2008 Zenoss, Inc.  All Rights Reserved.
#
######################################################################

import logging
log = logging.getLogger()

from Products.ZenUtils.PkgResources import pkg_resources
from Products.CMFCore.utils import ProductsPath

# Iterate over all ZenPack eggs and load them
for zpkg  in pkg_resources.iter_entry_points('zenoss.zenpacks'):
    try:
        pkg_path = zpkg.load().__path__[0]
        if pkg_path not in ProductsPath:
            ProductsPath.insert(0, pkg_path)
        __import__(zpkg.module_name)
    except Exception, e:
        log.exception(e)

