###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, 2009 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

"""Nagios

Uses the Nagios API defintions from
http://nagios.sourceforge.net/docs/3_0/pluginapi.html and from
http://nagiosplug.sourceforge.net/developer-guidelines.html#PLUGOUTPUT
"""

import re

from Products.ZenUtils.Utils import getExitMessage
from Products.ZenRRD.CommandParser import CommandParser

# Performance datapoints syntax
# Matches substrings having the form <key>=<value> with optional trailing
# whitespace.  E.g. if this is the perf data:
#
#     rta=0.337000ms;180.000000;300.000000;0.000000 pl=0%;100;100;0.
#
# this is the output (using findall()):
#
# [('rta=0.337000ms;180.000000;300.000000;0.000000', 'rta', '', '0.337000'),
#  ('pl=0%;100;100;0', 'pl', '', '0')]
#
perfParser = re.compile(r"""(([^ =']+|'([^']+)')=([-0-9.eE]+)\S*)""")


class _BadData(Exception):
    """
    Raised by splitMultLine when plugin output is not parseable.
    """


class Nagios(CommandParser):

    @staticmethod
    def splitMultiLine(output):
        """
        Convert the plugin output into component parts:
             summary, performance_data
        Empty output or no performance data raises a _BadData exception.
        """
        output = output.strip()
        if not output:
            raise _BadData("No output from plugin")

        # Expected format is:
        #
        #    <text>|<perf data>
        #    <extra text>
        #    <extra text>|<extra perf data>
        #    <extra perf data>
        #
        # The first line has text and, optionally, perf data.  Subsequent
        # lines will have the format of <text>|<perf> across multiple lines.
        lines = output.splitlines()
        firstLine = lines[0].strip()
        additionalLines = ' '.join(lines[1:])
        text, perf = [], []
        # Extract text and data from first line
        segments = firstLine.split('|')
        # If there are any segments, the first segment is text.
        if segments:
            text.append(segments.pop(0))
        # Extract additional text (due to bad pipe usage)
        while len(segments) > 1:
            text.append(segments.pop(0))
        # Extract the perf data (if exists)
        if segments:
            perf.append(segments.pop(0))
        # Now extract any additional data that may exist.
        if additionalLines:
            # Split text and perf data apart
            segments = additionalLines.split('|')
            # Extract text data (if any)
            if segments:
                text.extend(segments.pop(0).splitlines())
            # Extract perf data (if any)
            if segments:
                perf.extend(segments.pop(0).splitlines())

        # No perf data is an error
        if not perf:
            raise _BadData("No performance data from plugin")

        return text, perf

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

        for _, label, quote_label, value in perfParser.findall(all_data):
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

        evt = {
                "device": cmd.deviceConfig.device,
                "message": output,
                "severity": severity,
                "component": cmd.component,
                "eventKey": cmd.eventKey,
                "eventClass": cmd.eventClass,
            }
        try:
            summary, rawPerfData = self.splitMultiLine(output)
        except _BadData as ex:
            evt.update({
                "error_codes": "Datasource: %s - Code: %s - Msg: %s" % (
                   cmd.name, exitCode, getExitMessage(exitCode)
                ),
                "performanceData": None,
                "summary": str(ex),
            })
        else:
            evt.update({
                "performanceData": rawPerfData,
                "summary": summary,
            })
            perfData = self.processPerfData(rawPerfData)
            for dp in cmd.points:
                if dp.id in perfData:
                    result.values.append((dp, perfData[dp.id]))
        result.events.append(evt)
