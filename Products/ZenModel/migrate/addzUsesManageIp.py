##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''
Add addzUsesManageIp z property.  Generally true.
'''

import Migrate


class addzUsesManageIp(Migrate.Step):

    version = Migrate.Version(115, 0, 0)

    def cutover(self, dmd):
        if not hasattr(dmd.Devices, 'zUsesManageIp'):
            dmd.Devices._setProperty('zUsesManageIp', True, type='boolean')


addzUsesManageIp()
