######################################################################
#
# Copyright 2008 Zenoss, Inc.  All Rights Reserved.
#
######################################################################

import logging
log = logging.getLogger()

import Products
from Products.Five import zcml
from Products.CMFCore.utils import ProductsPath
from Products.ZenUtils.PkgResources import pkg_resources

# Helpfully load basic directives packs will probably use
zcml.load_config('meta.zcml', Products.Five)
zcml.load_config('permissions.zcml', Products.ZenModel)

# Iterate over all ZenPack eggs and load them
for zpkg  in pkg_resources.iter_entry_points('zenoss.zenpacks'):
    try:
        pkg_path = zpkg.load().__path__[0]
        if pkg_path not in ProductsPath:
            ProductsPath.insert(0, pkg_path)

        fromlist = zpkg.module_name.split('.')[:-1]
        module = __import__(zpkg.module_name, globals(), locals(), fromlist)

        # Try to load the pack's configuration for Zope 3 goodness
        try:
            zcml.load_config('configure.zcml', module)
        except IOError:
            # No configure.zcml defined in this pack; move on
            pass

    except Exception, e:
        log.exception(e)
