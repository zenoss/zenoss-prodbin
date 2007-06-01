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
        obids = [
            'Macos 10.4.1',
            'Macos 10.4.2',
            'Macos 10.4.3',
            'Linux 2.6.15-1.2054_FC5',
            'Linux 2.6.18-1.2798.fc6',
            'Linux 2.6.16-gentoo-r13',
            'IBM AIX version_ 05.02.0000.0050',
            'Linux 2.4.20',
            'Microsoft Windows 2000 Advanced Server',
            'Microsoft Windows 2000 Resource Kit',
            'Microsoft Windows 2000 Server',
            'Microsoft Windows NT Server',
            'Microsoft Windows NT Server Enterprise',
            'Microsoft Windows Server 2003, Enterprise Edition',
            'Microsoft Windows Server 2003, Enterprise Edition Service Pack 1',
            'Microsoft Windows Server 2003, Standard Edition',
            'Microsoft Windows Server 2003, Standard Edition',
            'Microsoft Windows Server 2003, Standard Edition Service Pack 1',
            'Suse',
            'Linux 2.4.20-30_37.rh9.at',
            'Linux 2.4.20-46.7.legacy',
            'Linux 2.6.11-1.14_FC3',
            'Linux 2.6.9-34.0.2.ELsmp',
            'Linux 2.6.9-34.EL',
            'Linux 2.6.9-42.ELsmp',
            'Linux 2.6.9-5.ELsmp',
            'REL ES 4.3',
            'SunOS 5.8',
            'Linux 2.6.17-10-server',
            'VMware Server',
            'Linux 1.0.3']
        if product.id in obids: product.isOS = True

convertOSSoftwareClass()
