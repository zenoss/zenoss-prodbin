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

