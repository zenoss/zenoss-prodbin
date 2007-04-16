#! /usr/bin/env python 
#################################################################
#
#   Copyright (c) 2007 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''ThresholdManager

Classes for managing the monitoring and reporting of thresholds.
'''

from Products.ZenEvents import Event


class Threshold:
    'Hold threshold config and send events based on the current value'
    
    count = 0
    label = ''
    minimum = None
    maximum = None
    eventClass = None
    severity = Event.Info
    escalateCount = 0

    def __init__(self, label, minimum, maximum, eventClass, severity, count):
        self.label = label
        self.update(minimum, maximum, eventClass, severity, count)


    def update(self, minimum, maximum, eventClass, severity, count):
        self.minimum = minimum
        self.maximum = maximum
        self.eventClass = eventClass
        self.severity = severity
        self.escalateCount = count


    def check(self, device, cname, oid, value, eventCb):
        'Check the value for min/max thresholds, and post events'
        if value is None:
            return
        thresh = None
        if self.maximum is not None and value > self.maximum:
            thresh = self.maximum
            how = 'exceeded'
        if self.minimum is not None and value < self.minimum:
            thresh = self.minimum
            how = 'not met'
        if thresh is not None:
            self.count += 1
            severity = self.severity
            if self.escalateCount and self.count >= self.escalateCount:
                severity += 1
            summary = '%s %s threshold of %s %s: current value %.2f' % (
                device, self.label, thresh, how, float(value))
            eventCb(device=device,
                    summary=summary,
                    eventClass=self.eventClass,
                    eventKey=oid,
                    component=cname,
                    severity=severity)
        else:
            if self.count:
                summary = '%s %s threshold restored current value: %.2f' % (
                    device, self.label, value)
                eventCb(device=device,
                        summary=summary,
                        eventClass=self.eventClass,
                        eventKey=oid,
                        component=cname,
                        severity=Event.Clear)
            self.count = 0

class ThresholdManager:
    "manage a collection of thresholds"
    
    def __init__(self):
        self.thresholds = {}

    def update(self, config):
        before = self.thresholds
        self.thresholds = {}
        for label, minimum, maximum, eventClass, severity, count in config:
            t = before.get(label, None)
            if t:
                t.update(minimum, maximum, eventClass, severity, count)
            else:
                t = Threshold(label, minimum, maximum, eventClass, severity, count)
            self.thresholds[label] = t

    def __iter__(self):
        return iter(self.thresholds.values())

