###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """MailProcessor
Base class module that other servers will subclass.
"""

import email, socket, rfc822, types
import calendar
from datetime import tzinfo, timedelta, datetime

from Event import Event

from Products.ZenUtils.Utils import unused

import logging
log = logging.getLogger("zen.mail")


class MailEvent(Event):
    """
    Defaults for events created by the processor
    """
    agent="zenmail"
    eventGroup="mail" 


# The following is copied from the Python standard library
# examples page: http://docs.python.org/library/datetime.html
ZERO = timedelta(0)

# A class building tzinfo objects for fixed-offset time zones.
# Note that FixedOffset(0, "UTC") is a different way to build a
# UTC tzinfo object.
class FixedOffset(tzinfo):
    """Fixed offset in minutes east from UTC."""

    def __init__(self, offset, name):
        self.__offset = timedelta(minutes = offset)
        self.__name = name

    def utcoffset(self, unused):
        return self.__offset

    def tzname(self, unused):
        return self.__name

    def dst(self, dt):
        return ZERO



class MessageProcessor(object):
    """
    Base class for parsing email messages that are retrieved via POP or
    received via SMTP.
    """

    def __init__(self, zem, defaultSeverity = 2): 
        """
        Initializer

        @param zem: class that provides sendEvent() method
        @type zem: Zenoss event manager object
        @param defaultSeverity: severity level to use if we can't figure one out
        @type defaultSeverity: integer
        """
        self.zem = zem
        self.eventSeverity = defaultSeverity


    def process(self, messageStr):
        """
        Convert an e-mail message into a Zenoss event.

        @param messageStr: e-mail message
        @type messageStr: string
        """
        message = email.message_from_string(messageStr)
        self.message = message
        
        fromAddr = message.get('From')
        log.debug("Found a 'from' address of %s" % fromAddr)
        if not fromAddr or fromAddr.find('@') == -1:
            log.warning("Unable to process the 'from' address %s -- ignoring mail" \
                        % fromAddr)
            return
        
        fromAddr = message.get('From').split('@')[1].rstrip('>')
        fromAddr = fromAddr.split(' ')[0]
        log.debug("The from address after processing is '%s'" % fromAddr)
        try:
            fromIp = socket.gethostbyname(fromAddr)
        except socket.gaierror:
            fromIp = None
            log.info('Hostname lookup failed for host: %s' % fromAddr)

        subject = message.get('Subject')

        # This is tricky...  date comes in with an offset value that
        # represents the number of seconds of difference between the
        # parsed timezone and UTC.  The events database wants all time
        # as seconds since the epoch and treats it as UTC.  As a
        # result we have to use the datetime class to do the
        # conversion because the functions in the time module do all
        # kinds of covnersions "to be helpful"
        t = rfc822.parsedate_tz(message.get('Date'))

        offset_secs = t[-1]

        # Convert the offset in seconds to minutes.  calendar wants minutes
        offset_mins = offset_secs / 60
        tz = FixedOffset(offset_mins, "Unknown")

        # Construct dt using the date and time as well as the timezone 
        dt = datetime(t[0], t[1], t[2], t[3], t[4], t[5], 0, tz)
        secs = calendar.timegm(dt.utctimetuple())
        log.info('Timestamp of the event (should be in UTC): %f' % secs)

        event = MailEvent(device=fromAddr, rcvtime=secs)
        if fromIp:
            event.ipAddress = fromIp

        payloads = message.get_payload()
        payload = 'This is the default message'
        while type(payloads) == types.ListType:
            payloads = payloads[0].get_payload()
        if type(payloads) == types.StringType:
            payload = payloads

        body = payload
        event.summary = subject
        event.message = body
        self.enrich(event, subject)

        event = self.buildEventClassKey(event)
        log.info('Sending event...')
        self.zem.sendEvent(event.__dict__)
        log.info('The event has been sent.')


    def enrich(self, event, subject):
        """
        Sanitize the event facility and severity fields.

        @param event: event
        @type event: simple class
        @param subject: e-mail subject (unused)
        @type subject: string
        """
        unused(subject)
        event.facility = "unknown"
        event.severity = self.eventSeverity
        

    def buildEventClassKey(self, evt):
        """
        Set the Zenoss eventClassKey

        @param evt: event
        @type evt: simple class
        @return: modified event
        @rtype: simple class
        """
        if getattr(evt, 'eventClassKey', '') or getattr(evt, 'eventClass', ''):
            return evt
        elif getattr(evt, 'ntevid', ''):
            evt.eventClassKey = "%s_%s" % (evt.component,evt.ntevid)
        elif getattr(evt, 'component', ''):
            evt.eventClassKey = evt.component
        else:
            evt.eventClassKey = 'email'

        if getattr(evt, 'eventClassKey', ''):
            log.debug("eventClassKey=%s", evt.eventClassKey)
        else:
            log.debug("No eventClassKey assigned")
        return evt



class POPProcessor(MessageProcessor):
    """
    Extension point for messages received via POP.  If you need to
    override the behavior of "process" you should do so by
    implementing it here.
    """

    def __init__(self, zem, defaultSeverity = 2): 
        """
        Initializer

        @param zem: class that provides sendEvent() method
        @type zem: Zenoss event manager object
        @param defaultSeverity: severity level to use if we can't figure one out
        """
        MessageProcessor.__init__(self, zem, defaultSeverity)



class MailProcessor(MessageProcessor):
    """
    Extension point for messages received via SMTP.  If you need to
    override the behavior of "process" you should do so by
    implementing it here.
    """

    def __init__(self, zem, defaultSeverity = 2): 
        """
        Initializer

        @param zem: class that provides sendEvent() method
        @type zem: Zenoss event manager object
        @param defaultSeverity: severity level to use if we can't figure one out
        """
        MessageProcessor.__init__(self, zem, defaultSeverity)

