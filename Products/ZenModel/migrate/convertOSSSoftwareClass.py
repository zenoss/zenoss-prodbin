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

__doc__='''

Convert all OSSSoftwareClass objects to SoftwareClass

$Id:$
'''
import Migrate
from Products.ZenModel.SoftwareClass import SoftwareClass, OSSoftwareClass

class convertOSSoftwareClass(Migrate.Step):
    version = Migrate.Version(2, 0, 0)

    def cutover(self, dmd):
        for prod in dmd.Manufacturers.getProductsGen():
            self.convert(prod)

    def convert(self, product):
        if product.__class__ == OSSoftwareClass:
            product.__class__ = SoftwareClass
            product.isOS = True


convertOSSoftwareClass()