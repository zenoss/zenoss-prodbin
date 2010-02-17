###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Products.ZenRRD.CommandParser import CommandParser
from Products.ZenUtils.Utils import prepId as globalPrepId
import re
from pprint import pformat
import logging

log = logging.getLogger("zen.ComponentCommandParser")

class ComponentCommandParser(CommandParser):

    componentSplit = '\n'

    componentScanner = ''

    scanners = ()

    componentScanValue = 'id'

    def prepId(self, id, subchar='_'):
        return globalPrepId(id, subchar)

    def dataForParser(self, context, dp):
        return dict(componentScanValue = getattr(context, self.componentScanValue))

    def processResults(self, cmd, result):

        # Map datapoints by data you can find in the command output
        ifs = {}
        for dp in cmd.points:
            dp.component = dp.data['componentScanValue']
            points = ifs.setdefault(dp.component, {})
            points[dp.id] = dp

        # split data into component blocks
        parts = cmd.result.output.split(self.componentSplit)

        for part in parts:
            # find the component match
            match = re.search(self.componentScanner, part)
            if not match: continue
            component = match.groupdict()['component'].strip()
            if self.componentScanValue == 'id': component = self.prepId(component)
            points = ifs.get(component, None)
            if not points: continue

            # find any datapoints
            for search in self.scanners:
                match = re.search(search, part)
                if match:
                    for name, value in match.groupdict().items():
                        dp = points.get(name, None)
                        if dp is not None:
                            if value in ('-', ''): value = 0
                            result.values.append( (dp, float(value) ) )
                            
        log.debug(pformat(result))
        return result
    
