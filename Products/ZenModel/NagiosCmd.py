###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from Products.ZenRelations.RelSchema import *

from ZenModelRM import ZenModelRM


import warnings
warnings.warn("NagiosCmd is deprecated", DeprecationWarning)
class NagiosCmd(ZenModelRM):

    _relations =  (
        ("nagiosTemplate", ToOne(ToManyCont, "Products.ZenModel.NagiosTemplate", "nagiosCmds")),
    )    

    security = ClassSecurityInfo()

InitializeClass(NagiosCmd)

