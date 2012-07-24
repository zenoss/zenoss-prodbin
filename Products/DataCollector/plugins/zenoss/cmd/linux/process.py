##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """process
Linux command plugin for parsing ps command output and modeling processes.
"""

from Products.DataCollector.ProcessCommandPlugin import ProcessCommandPlugin

class process(ProcessCommandPlugin):
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
