#! /usr/bin/env python 
#################################################################
#
#   Copyright (c) 2007 Zenoss, Inc. All rights reserved.
#
#################################################################

import email, socket, time, rfc822
import calendar
from datetime import tzinfo, timedelta, datetime

from Event import Event

import logging
log = logging.getLogger("zen.mail")


class MailEvent(Event):
    agent="zenmail"
    eventGroup="mail" 


ZERO = timedelta(0)

# A class building tzinfo objects for fixed-offset time zones.
# Note that FixedOffset(0, "UTC") is a different way to build a
# UTC tzinfo object.
class FixedOffset(tzinfo):
    """Fixed offset in minutes east from UTC."""

    def __init__(self, offset, name):
        self.__offset = timedelta(minutes = offset)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return ZERO


class MessageProcessor(object):
    def __init__(self, zem): 
        self.zem = zem


    def process(self, messageStr):
        message = email.message_from_string(messageStr)
        fromAddr = message.get('From').split('@')[1][:-1]
        try:
            fromIp = socket.gethostbyname(fromAddr)
        except socket.gaierror, e:
            fromIp = None
            log.error('hostname lookup failed for host: %s' % fromAddr, exc_info=1)

        subject = message.get('Subject')

        # this is tricky...  date comes in with an offset value that
        # represents the number of seconds of difference between the
        # parsed timezone and UTC.  the events database wants all time
        # as seconds since the epoch and treats it as UTC.  as a
        # result we have to use the datetime class to do the
        # conversion because the functions in the time module do all
        # kinds of covnersions "to be helpful"
        t = rfc822.parsedate_tz(message.get('Date'))

        offset_secs = t[-1]

        # convert the offset in seconds to minutes.  calendar wants minutes
        offset_mins = offset_secs / 60
        tz = FixedOffset(offset_mins, "Unknown")

        # construct dt using the date and time as well as the timezone 
        dt = datetime(t[0], t[1], t[2], t[3], t[4], t[5], 0, tz)
        secs = calendar.timegm(dt.utctimetuple())
        log.info('timestamp of event (should be in UTC): %f' % secs)

        event = MailEvent(device=fromAddr, ipAddress=fromIp, rcvtime=secs)

        body = message.get_payload()
        event.summary = body
        self.enrich(event, subject)

        event = self.buildEventClassKey(event)
        log.info('sending event...')
        self.zem.sendEvent(event)


    def enrich(self, event, subject):
        pri = self.zem.defaultPriority
        event.priority = pri
        event.facility = "unknown"
        event.severity = 5


    def buildEventClassKey(self, evt):
        if hasattr(evt, 'eventClassKey') or hasattr(evt, 'eventClass'):
            return evt
        elif hasattr(evt, 'ntevid'):
            evt.eventClassKey = "%s_%s" % (evt.component,evt.ntevid)
        elif hasattr(evt, 'component'):
            evt.eventClassKey = evt.component
        if hasattr(evt, 'eventClassKey'): 
            log.debug("eventClassKey=%s", evt.eventClassKey)
        else:
            log.debug("no eventClassKey assigned")
        return evt
