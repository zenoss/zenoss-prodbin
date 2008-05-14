
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


from Products.ZenRelations.RelSchema import *

class TemplateContainer(object):
    """
    This mixin is so that different classes can sit on the other
    end of the RRDTemplate.deviceClass method.
    """

    meta_type = 'TemplateContainer'

    _relations = (
        # deviceClass is named as such for sad, historical reasons.
        # Currently the subclasses of TemplateContainer are either
        # a DeviceClass or a MonitorClass.
        ('rrdTemplates', 
            ToManyCont(ToOne, 'Products.ZenModel.RRDTemplate', 'deviceClass')),
    )

