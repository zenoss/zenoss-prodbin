# ##########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
# ##########################################################################

import logging
log = logging.getLogger()

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
        log.exception(e)

