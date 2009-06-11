###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__='''

Update the regexes on manufacturers so that a variety of different manufacturer
names all get mapped to the same manufacturer within Zenoss.

'''
import Migrate

manuRegexes = {
    'Apple': ('^Apple Computer',),
    'Broadcom': ('^Broadcom Corp$',),
    'Cisco': ('^ciscoSystems$',),
    'Dell': ('^Dell Inc\.$',),
    'F5 Networks': ('^F5 Networks Inc$',),
    'HP': ('Hewlett\-Packard',),
    'Intel': ('^Intel Corporation$',),
    'Microsoft': ('^Microsoft Corporation$',),
    'Net-SNMP': ('^net snmp$',),
    'Nortel': ('^Nortel Networks$',),
    'Sun': ('^Sun Microsystems',),
    'VMware': ('^VMware, Inc.$',),
    'WinZip': ('^WinZip Computing',),
    'XGI': ('^XGI Xabre Graphics Inc$',),
    }

class updateManufacturerRegexes(Migrate.Step):
    version = Migrate.Version(2, 4, 1)
    
    def cutover(self, dmd):
        for mname, regexes in manuRegexes.items():
            m = dmd.Manufacturers.getManufacturer(mname)

            # Don't update manufacturers that already have regexes set.
            if m.regexes: continue

            m.regexes = regexes

updateManufacturerRegexes()

