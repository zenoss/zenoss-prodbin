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

from Products.DataCollector.ProcessCommandPlugin import ProcessCommandPlugin

class process(ProcessCommandPlugin):
    """
    Linux command plugin for parsing ps command output and modeling processes.
    """
    
    
    command = 'ps axho args'
    
    
    def condition(self, device, log):
        """
        If the device resides under the Server/SSH device class, then always
        run this plugin.  Otherwise only run this plugin if uname has been
        previously modeled as "Linux".
        """
        path = device.deviceClass().getPrimaryUrlPath()
        
        if path.startswith("/zport/dmd/Devices/Server/SSH"):
            result = True
        else:
            result = device.os.uname == 'Linux'
            
        return result
        