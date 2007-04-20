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
#!/usr/bin/env python

import Globals
from Products.ZenUtils.ZCmdBase import ZCmdBase

class ReportRunner(ZCmdBase):

    def main(self):
        plugin =  self.args[0]
        args = {}
        for a in self.args[1:]:
            if a.find('=') > -1:
                key, value = a.split('=', 1)
                args[key] = value
        self.log.debug("Running '%s' with %r", plugin, args)
        result = self.dmd.ReportServer.plugin(plugin, args)
        import pprint
        pprint.pprint(result)

if __name__ == '__main__':
    rr = ReportRunner()
    rr.main()


