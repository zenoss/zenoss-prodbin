###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Products.ZenTestCase.BaseTestCase import BaseTestCase


class ZenRelationsBaseTest(BaseTestCase):
    """
    Use this class to provide ZenRelations-specific setup, etc., for
    ZenRelations unit tests.
    """

    def build(self, context, klass, id):
        """create instance attache to context and build relationships"""
        return self.create(context, klass, id)

