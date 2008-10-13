######################################################################
#
# Copyright 2008 Zenoss, Inc.  All Rights Reserved.
#
######################################################################

import logging
log = logging.getLogger()

from Products.ZenUtils.PkgResources import pkg_resources

# Iterate over all ZenPack eggs and load them
for zpkg  in pkg_resources.iter_entry_points('zenoss.zenpacks'):
    try:
        __import__(zpkg.module_name)
    except Exception, e:
        log.exception(e)
