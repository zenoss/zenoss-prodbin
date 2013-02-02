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
