##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """SetIgnoreParamsOnZenDaemons

Change zenmail, zentrap, and zensyslog OSProcess monitoring definitions to ignore arguments
"""

import Migrate

class SetIgnoreParamsOnZenDaemons(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        try:
            classes = dmd.Processes.Zenoss.osProcessClasses()
        except AttributeError:
            return
        for osproc in classes:
            if osproc.name in ('zentrap', 'zenmail', 'zensyslog') and \
               osproc.regex in ('.*zentrap.py.*', '.*zenmail.py.*', '.*zensyslog.py.*'):
                osproc.ignoreParameters = True

SetIgnoreParamsOnZenDaemons()
