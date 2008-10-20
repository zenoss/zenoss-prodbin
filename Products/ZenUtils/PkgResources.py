###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

# _xmlplus is included in two packages, so we get an annoying UserWarning when
# we import pkg_resources. If everything imports from here, we can filter out
# the warning centrally.
import warnings
warnings.filterwarnings('ignore', '.*_xmlplus.*', UserWarning)

# There is a nasty incompatibility between pkg_resources and twisted.
# Importing pkg_resources before the twisted reactor works around the problem.
# See http://dev.zenoss.org/trac/ticket/3146 for details
import pkg_resources

from Products.ZenUtils.Utils import unused
unused(pkg_resources)

__all__ = ['pkg_resources']
