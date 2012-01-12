###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

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

