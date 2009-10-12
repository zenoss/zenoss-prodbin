###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, 2009 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """Nagios
Uses the Nagios API defintions from http://nagios.sourceforge.net/docs/3_0/pluginapi.html
and from
http://nagiosplug.sourceforge.net/developer-guidelines.html#PLUGOUTPUT
"""

import re

# Performance datapoints syntax
perfParser = re.compile(r"""(([^ =']+|'([^']+)')=([-0-9.eE]+)\S*)""")

from Products.ZenUtils.Utils import getExitMessage
from Products.ZenRRD.CommandParser import CommandParser

class Nagios(CommandParser):

    def splitMultiLine(self, output):
        """
        Convert the plugin output into component parts:
             summary, message, performance_data

        If the message is None, then there is an error.
        """
        summary, msg, rawPerfData = "", [], []
        if not output.strip():
            return "No output from plugin", None, None

        # Deal with the first line
        first_plus_rest = output.split('\n',1)
        firstLine = first_plus_rest[0].strip()
        if not firstLine:
            return "No output from plugin", None, None

        summaryNPerf = firstLine.split('|')
        if len(summaryNPerf) > 2:
            return "Too many |'s in output from plugin", None, None

        summary = summaryNPerf[0]
        # x = [] so x[1] is an error but x[1:] == []
        rawPerfData = summaryNPerf[1:]

        # Is there a mult-line to deal with?
        multi = first_plus_rest[1:]
        if not multi: # Nope
            return summary, summary, rawPerfData

        service_output_plus_perf = multi[0].split('|')
        if len(service_output_plus_perf) > 2:
            return "Too many |'s in output from plugin", None, None

        msg = service_output_plus_perf[0]
        if len(service_output_plus_perf) == 2:
            rawPerfData += service_output_plus_perf[1].split('\n')
        return summary, msg, rawPerfData


    def processPerfData(self, rawPerfData):
        """
        Create a dictionary of datapoint:value entries from
        the plugin output. 
        This funtion removes a ' (represented as '' in the label)
        from the label.  There's just too much opportunity to mess
        something up by keeping a shell meta-character.
        """
        perfData = {}
        all_data = ' '.join(rawPerfData)
        # Strip out all '' strings
        all_data = all_data.replace("''", "")

        for full_match, label, quote_label, value in perfParser.findall(all_data):
            if quote_label:
                label = quote_label
            try:
                value = float(value.strip())
            except:
                value = 'U'
            perfData[label] = value

        return perfData


    def processResults(self, cmd, result):
        output = cmd.result.output
        exitCode = cmd.result.exitCode
        severity = cmd.severity
        if exitCode == 0:
            severity = 0
        elif exitCode == 2:
            severity = min(severity + 1, 5)

        summary, msg, rawPerfData = self.splitMultiLine(output)

        evt = dict(device=cmd.deviceConfig.device,
              summary=summary, message=output,
              severity=severity, component=cmd.component,
              eventKey=cmd.eventKey, eventClass=cmd.eventClass,
              performanceData=rawPerfData,
        )

        if msg is None:
            evt['error_codes'] = 'Cmd: %s - Code: %s - Msg: %s' % (
                           cmd.command, exitCode,
                           getExitMessage(exitCode))
            result.events.append(evt)
            return

        result.events.append(evt)

        perfData = self.processPerfData(rawPerfData)
        for dp in cmd.points:
            if dp.id in perfData:
                result.values.append( (dp, perfData[dp.id]) )

