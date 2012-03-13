###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Products.Zuul.interfaces import IInfo
from Products.Zuul.form import schema
from Products.Zuul.utils import ZuulMessageFactory as _t
from zope.schema.vocabulary import SimpleVocabulary
import textwrap


def getNotificationBodyTypes():
    return ['html', 'text']

class IEmailActionContentInfo(IInfo):

    body_content_type = schema.Choice(
        title       = _t(u'Body Content Type'),
        vocabulary  = SimpleVocabulary.fromValues(getNotificationBodyTypes()),
        description = _t(u'The content type of the body for emails.'),
        default     = u'html'
    )

    subject_format = schema.TextLine(
        title       = _t(u'Message (Subject) Format'),
        description = _t(u'The template for the subject for emails.'),
        default     = _t(u'[zenoss] ${evt/device} ${evt/summary}')
    )

    body_format = schema.Text(
        title       = _t(u'Body Format'),
        description = _t(u'The template for the body for emails.'),
        default     = textwrap.dedent(text = u'''
        Device: ${evt/device}
        Component: ${evt/component}
        Severity: ${evt/severity}
        Time: ${evt/lastTime}
        Message:
        ${evt/message}
        <a href="${urls/eventUrl}">Event Detail</a>
        <a href="${urls/ackUrl}">Acknowledge</a>
        <a href="${urls/closeUrl}">Close</a>
        <a href="${urls/eventsUrl}">Device Events</a>
        ''')
    )

    clear_subject_format = schema.TextLine(
        title       = _t(u'Clear Message (Subject) Format'),
        description = _t(u'The template for the subject for CLEAR emails.'),
        default     = _t(u'[zenoss] CLEAR: ${evt/device} ${evt/summary}/${clearEvt/summary}')
    )

    clear_body_format = schema.Text(
        title       = _t(u'Body Format'),
        description = _t(u'The template for the body for CLEAR emails.'),
        default     = textwrap.dedent(text = u'''
        Event: '${evt/summary}'
        Cleared by: '${evt/clearid}'
        At: ${evt/stateChange}
        Device: ${evt/device}
        Component: ${evt/component}
        Severity: ${evt/severity}
        Message:
        ${evt/message}
        <a href="${urls/reopenUrl}">Reopen</a>
        ''')
    )

    email_from = schema.Text(
        title       = _t(u'From Address for Emails'),
        description = _t(u'The user from which the e-mail originated on the Zenoss server.'),
    )

    host = schema.Text(
        title       = _t(u'SMTP Host'),
        description = _t(u'Simple Mail Transport Protocol (aka E-mail server).'),
    )

    port = schema.Int(
        title       = _t(u'SMTP Port (usually 25)'),
        description = _t(u'TCP/IP port to access Simple Mail Transport Protocol (aka E-mail server).'),
    )

    useTls = schema.Bool(
        title       = _t(u'Use TLS?'),
        description = _t(u'Use Transport Layer Security for E-mail?')
    )

    user = schema.Text(
        title       = _t(u'SMTP Username (blank for none)'),
        description = _t(u'Use this only if authentication is required.'),
    )

    password = schema.Password(
        title       = _t(u'SMTP Password (blank for none)'),
        description = _t(u'Use this only if authentication is required.'),
    )


class IPageActionContentInfo(IInfo):

    subject_format = schema.TextLine(
        title       = _t(u'Message (Subject) Format'),
        description = _t(u'The template for the subject for pages.'),
        default     = _t(u'[zenoss] ${evt/device} ${evt/summary}')
    )

    clear_subject_format = schema.TextLine(
        title       = _t(u'Clear Message (Subject) Format'),
        description = _t(u'The template for the subject for CLEAR pages.'),
        default     = _t(u'[zenoss] CLEAR: ${evt/device} ${evt/summary}/${clearEvt/summary}')
    )


class ICommandActionContentInfo(IInfo):

    action_timeout = schema.Int(
        title       = _t(u'Command Timeout (seconds)'),
        description = _t(u'How long before the command times out.'),
        default     = 60
    )

    body_format = schema.Text(
        title       = _t(u'Command'),
        description = _t(u'The template for the body for commands.')
    )

    clear_body_format = schema.Text(
        title       = _t(u'Clear Command'),
        description = _t(u'The template for the body for CLEAR commands.')
    )

    user_env_format = schema.Text(
        title       = _t(u'Environment variables'),
        description = _t(u'A semi-colon separated list of environment variables.'),
    )


class ISnmpTrapActionContentInfo(IInfo):

    action_destination = schema.TextLine(
        title       = _t(u'SNMP Trap Destination'),
        description = _t(u'The template for the subject for the SNMP trap destination.'),
        default     = _t(u'traphost')
    )

    community = schema.Text(
        title       = _t(u'SNMP Community'),
        description = _t(u'SNMP authentication string.'),
        default = _t(u'public')
    )

    version = schema.Choice(
        title       = _t(u'SNMP Version'),
        description = _t(u'SNMP trap protocol version.'),
        vocabulary  = SimpleVocabulary.fromValues(['v1', 'v2c']),
        default = _t(u'v2c')
    )

    port = schema.Int(
        title       = _t(u'SNMP Port (usually 162)'),
        description = _t(u'Port number used by the SNMP trap receiver process.'),
        default = 162
    )
