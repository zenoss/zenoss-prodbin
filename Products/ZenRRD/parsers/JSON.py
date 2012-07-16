###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

"""JSON

General purpose JSON parser for handling JSON objects matching the following
template. This allows many datapoints for many components to be collected
from a single COMMAND datasource. It also allows for collection of many
events from a single COMMAND datasource.

{
    "values": {
        "component_id_1": {
            "datapoint1": 123.4,
            "datapoint2": 987.6
        },

        "component_id_2": {
            "datapoint1": 56.7,
            "datapoint2": 54.3
        }
    },

    "events": [
        {
            "severity": 2,
            "other_field_1": "value for other field",
            "summary": "event summary"
        },

        {
            "severity": 3,
            "other_field_1": "another value for other field",
            "summary": "another event summary"
        }
    ]
}

"""

import json

from Products.ZenRRD.CommandParser import CommandParser


def stringify_keys(dictionary):
    """Convert all keys of given dictionary to strings.

    During serialization and deserialization between the collector and hub we
    need to enforce that dictionary keys are plan, not unicode, strings.

    """
    fixed_dictionary = {}
    for k, v in dictionary.items():
        fixed_dictionary[str(k)] = v

    return fixed_dictionary


class JSON(CommandParser):
    def processResults(self, cmd, result):
        data = None

        try:
            data = json.loads(cmd.result.output)
        except Exception, ex:
            # See NOTE below. If this event ever occurs it will not auto-clear.
            result.events.append({
                'severity': cmd.severity,
                'summary': 'error parsing command output',
                'eventKey': cmd.command,
                'eventClass': cmd.eventClass,
                'command_output': cmd.result.output,
                'exception': str(ex),
                })

            return

        # NOTE: It might be a good idea to send a clear event for the potential
        # parse error above. However, this would end up flooding clear events
        # that are almost always useless. I've chosen to trust the executed
        # plugin to always return JSON data of some sort.

        # Pass incoming events straight through.
        result.events.extend(map(stringify_keys, data.get('events', [])))

        # Map incoming values to their components and datapoints.
        if len(data.get('values', {}).keys()) > 0:
            for point in cmd.points:
                if point.component not in data['values']:
                    continue

                if point.id not in data['values'][point.component]:
                    continue

                result.values.append((
                    point, data['values'][point.component][point.id]))

        return result
