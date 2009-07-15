######################################################################
#
# Copyright 2008 Zenoss, Inc.  All Rights Reserved.
#
######################################################################

import logging
log = logging.getLogger()

from Products.ZenUtils.PkgResources import pkg_resources
from Products.CMFCore.utils import ProductsPath
from Products.ZenRelations.ZenPropertyManager import ZenPropertyManager
from Products.ZenRelations.ZenPropertyManager import PropertyDescriptor

# Iterate over all ZenPack eggs and load them
for zpkg  in pkg_resources.iter_entry_points('zenoss.zenpacks'):
    try:
        pkg_path = zpkg.load().__path__[0]
        if pkg_path not in ProductsPath:
            ProductsPath.insert(0, pkg_path)
            
        # fromlist is typically ZenPacks.zenoss
        fromlist = zpkg.module_name.split('.')[:-1]
        module = __import__(zpkg.module_name, globals(), locals(), fromlist)
        
        if hasattr(module, 'ZenPack'):
            # monkeypatch ZenPropertyManager adding an instance of the 
            # descriptor class for each of the zProperties in this ZenPack
            for id, value, type in module.ZenPack.packZProperties:
                setattr(ZenPropertyManager, id, PropertyDescriptor(id, type))
            
    except Exception, e:
        log.exception(e)

