#! /usr/bin/env python 
#################################################################
#
#   Copyright (c) 2007 Zenoss, Inc. All rights reserved.
#
#################################################################

import email, socket, time, rfc822

from Event import Event

import logging
log = logging.getLogger("zen.mail")


class MailEvent(Event):
    agent="zenmail"
    eventGroup="mail" 


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
        rtime = rfc822.parsedate_tz(message.get('Date'))
        tz_offset = rtime[-1]
        rtime_secs = time.mktime(rtime[0:9]) - tz_offset

        body = message.get_payload()
        
        event = MailEvent(device=fromAddr, ipAddress=fromIp, rcvtime=rtime_secs)
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
