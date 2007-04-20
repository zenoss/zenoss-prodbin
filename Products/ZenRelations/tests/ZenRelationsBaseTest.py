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
#   Copyright (c) 2006 Zentinel Systems, Inc. All rights reserved.
from OFS.Folder import manage_addFolder
from Testing.ZopeTestCase import ZopeLite

from Products.ZenTestCase.BaseTestCase import BaseTestCase

from TestSchema import create, build, DataRoot

class ZenRelationsBaseTest(BaseTestCase):
    """
    Use this class to provide ZenRelations-specific setup, etc., for
    ZenRelations unit tests.
    """
    def create(self, context, klass, id):
        """create an instance and attach it to the context passed"""
        return create(context, klass, id)

    def build(self, context, klass, id):
        """create instance attache to context and build relationships"""
        return build(context, klass, id)

