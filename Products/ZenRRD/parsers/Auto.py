###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import re
# how to parse each value from a nagios command

from Nagios import perfParser as NagParser

#NagParser = re.compile(r"""(([^ =']+|'(.*)'+)=([-0-9.eE]+)([^;\s]*;?){0,5})""")
# how to parse each value from a cacti command
from Cacti import CacParser

from Products.ZenUtils.Utils import getExitMessage
from Products.ZenRRD.CommandParser import CommandParser

class Auto(CommandParser):


    def processResults(self, cmd, result):
        output = cmd.result.output
        output = output.split('\n')[0].strip()
        exitCode = cmd.result.exitCode
        severity = cmd.severity
        if output.find('|') >= 0:
            msg, values = output.split('|', 1)
        elif CacParser.search(output):
            msg, values = '', output
        else:
            msg, values = output, ''
        msg = msg.strip() or 'Datasource: %s - Code: %s - Msg: %s' % (
            cmd.name, exitCode, getExitMessage(exitCode))
        if exitCode != 0:
            if exitCode == 2:
                severity = min(severity + 1, 5)
            result.events.append(dict(device=cmd.deviceConfig.device,
                                      summary=msg,
                                      severity=severity,
                                      message=msg,
                                      performanceData=values,
                                      eventKey=cmd.eventKey,
                                      eventClass=cmd.eventClass,
                                      component=cmd.component))

        matches = NagParser.findall(values)
        labelIdx = 1
        valueIdx = 3
        if not matches:
            matches = CacParser.findall(values)
            labelIdx = 0
            valueIdx = 2

        for parts in matches or []:
            label = parts[labelIdx].replace("''", "'")
            try:
                value = float(parts[valueIdx])
            except Exception:
                value = 'U'
            for dp in cmd.points:
                if dp.id == label:
                    result.values.append( (dp, value) )
                    break

