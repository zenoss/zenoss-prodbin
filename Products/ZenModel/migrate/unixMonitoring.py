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

"""Adds Server/SSH and Server/SSH/Linux device classes
"""
import Migrate

class addUnixMonitoring(Migrate.Step):
    version = Migrate.Version(2, 5, 0)

    def cutover(self, dmd):
        server = dmd.findChild('Devices/Server')
        sshId = 'SSH'
        if not sshId in server.childIds():
            server.manage_addOrganizer(sshId)
            ssh = server.findChild(sshId)
            ssh.setZenProperty('zSnmpMonitorIgnore', True)
            ssh.setZenProperty('zCollectorPlugins', [])
        else:
            #previous versions added the zProps incorrectly
            ssh = server.findChild(sshId)
            from Acquisition import aq_base
            if hasattr(aq_base(ssh),'zSnmpMonitorIgnore'):
                del ssh.zSnmpMonitorIgnore
            ssh.setZenProperty('zSnmpMonitorIgnore', True)
            if hasattr(aq_base(ssh),'zCollectorPlugins'):
                del ssh.zCollectorPlugins
            ssh.setZenProperty('zCollectorPlugins', [])
            
        ssh = server.findChild(sshId)
        linuxId = 'Linux'
        if not linuxId in ssh.childIds():
            ssh.manage_addOrganizer(linuxId)

addUnixMonitoring()
