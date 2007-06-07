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

Set expectRegex property for IpService objects that need it

'''
import Migrate

class AddExpectRegex(Migrate.Step):
    version = Migrate.Version(2, 0, 0)

    def cutover(self, dmd):
        regexmap = {
            'tcp_00025' : r'220',
            'tcp_00110' : r'\+OK',
            'tcp_00587' : r'220',
            'tcp_00022' : r'SSH',
            'tcp_00143' : r'OK',
        }            

        for id in regexmap.keys():
            svc = dmd.Services.IpService.find(id)
            if svc:
                svc.expectRegex = regexmap[id]

AddExpectRegex()

