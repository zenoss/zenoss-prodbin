# ##########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
# ##########################################################################
import json
import os.path
import logging

log = logging.getLogger("zen.ZenossStartup")

from zope.dottedname.resolve import resolve
from Products.CMFCore.utils import ProductsPath

from zenoss.protocols.queueschema import schema as _global_schema

from Products.ZenUtils.PkgResources import pkg_resources

def load_qjs(pack_path):
    """
    Load one or more queue schema files from a ZenPack.
    They should live in PACK/protocols/*.qjs.
    """
    protocols_path = os.path.join(pack_path, 'protocols')
    if not os.path.isdir(protocols_path):
        return
    for fname in os.listdir(protocols_path):
        if fname.endswith('.qjs'):
            fullpath = os.path.abspath(os.path.join(protocols_path, fname))
            if not os.path.isfile(fullpath):
                continue
            with open(fullpath) as f:
                schema = json.load(f)
                _global_schema._load(schema)


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

        # Load any queue schema files
        load_qjs(pkg_path)

    except Exception, e:
        # This messes up logging a bit, but if we need to report
        # an error, this saves hours of trying to find out what's going on
        logging.basicConfig()
        log.exception("Error encountered while processing %s",
                      zpkg.module_name)
