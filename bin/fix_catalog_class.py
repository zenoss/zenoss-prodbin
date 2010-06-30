#############################################################################
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#############################################################################

#NOTE: this only runs in zendmd. run like this
#      zendmd ==script fix_catalog_class.py --commit
from Products.Zuul.catalog.global_catalog import GlobalCatalog
from Products.ZenUtils.MultiPathIndex import MultiPathIndex

# change the catalog's class to belong to the base
dmd.zport.global_catalog.__class__ = GlobalCatalog
dmd.zport.global_catalog._p_changed = True

# fix the multipath index class
for idx in dmd.zport.global_catalog.Indexes.objectValues():
    if idx.id == 'path':
        idx.__class__ = MultiPathIndex
        idx._p_changed = True
