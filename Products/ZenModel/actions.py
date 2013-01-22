##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import re
from socket import getaddrinfo
from traceback import format_exc
from zope.interface import implements
from zope.component import getUtilitiesFor

from pynetsnmp import netsnmp

from twisted.internet.protocol import ProcessProtocol

from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.Utils import formatdate

from zenoss.protocols.protobufs import zep_pb2
from Products.ZenEvents.events2.proxy import EventSummaryProxy
from Products.ZenUtils.Utils import sendEmail
from Products.Zuul.interfaces.actions import IEmailActionContentInfo, IPageActionContentInfo, ICommandActionContentInfo, ISnmpTrapActionContentInfo
from Products.Zuul.form.interfaces import IFormBuilder
from Products.ZenModel.UserSettings import GroupSettings
from Products.ZenModel.interfaces import IAction, IProvidesEmailAddresses, IProvidesPagerAddresses, IProcessSignal, INotificationContextProvider
from Products.ZenModel.NotificationSubscription import NotificationEventContextWrapper
from Products.ZenEvents.Event import Event
from Products.ZenUtils import Utils
from Products.ZenUtils.guid.guid import GUIDManager
from Products.ZenUtils.ProcessQueue import ProcessQueue
from Products.ZenEvents.ZenEventClasses import Warning as SEV_WARNING
from Products.ZenUtils.ZenTales import talEval

import logging

log = logging.getLogger("zen.actions")




class ActionExecutionException(Exception): pass


class ActionMissingException(Exception): pass


class TargetableActionException(ActionExecutionException):
    def __init__(self, action, notification, exceptionTargets):
        self.action = action
        self.notificationId = notification.id
        self.exceptionTargets = exceptionTargets
    def __str__(self):
        return "Failed {action} for notification {notification} on targets {targets}".format(
            action=self.action.name,
            notification=self.notificationId,
            targets = ','.join(self.exceptionTargets)
        )

def processTalSource(source, **kwargs):
    """
    This function is used to parse fields made available to actions that allow
    for TAL expressions.
    """
    sourceStr = source
    context = kwargs.get('here', {})
    context.update(kwargs)
    return talEval(sourceStr, context, kwargs)


def _signalToContextDict(signal, zopeurl, notification=None, guidManager=None):
    summary = signal.event
    # build basic event context wrapper for notifications
    if signal.clear:
        # aged and closed events have clear == True, but they don't have an associated clear event
        #   spoof a clear event in those cases, so the notification messages contain useful info
        if summary.status == zep_pb2.STATUS_AGED:
            occur = signal.clear_event.occurrence.add()
            occur.summary = "Event aging task aged out the event."
            summary.cleared_by_event_uuid = "Event aging task"
        elif summary.status == zep_pb2.STATUS_CLOSED:
            occur = signal.clear_event.occurrence.add()
            occur.summary = "User '" + summary.current_user_name + "' closed the event in the Zenoss event console."
            summary.cleared_by_event_uuid = "User action"
        data = NotificationEventContextWrapper(summary, signal.clear_event)
    else:
        data = NotificationEventContextWrapper(summary)

    # add urls to event context
    data['urls']['eventUrl'] = getEventUrl(zopeurl, summary.uuid)
    data['urls']['ackUrl'] = getAckUrl(zopeurl, summary.uuid)
    data['urls']['closeUrl'] = getCloseUrl(zopeurl, summary.uuid)
    proxy = EventSummaryProxy(summary)
    data['urls']['deviceUrl'] = _getBaseDeviceUrl(zopeurl, proxy.DeviceClass, proxy.device)
    data['urls']['eventsUrl'] = getEventsUrl(zopeurl, proxy.DeviceClass, proxy.device)
    data['urls']['reopenUrl'] = getReopenUrl(zopeurl, summary.uuid)
    data['urls']['baseUrl'] = zopeurl
    # now process all custom processors that might be registered to enhance
    # the event context
    for key, processor in getUtilitiesFor(IProcessSignal):
        data[key] = processor.process(signal)

    # Process INotificationContextProvider
    for key, contextProvider in getUtilitiesFor(INotificationContextProvider):
        contextProvider.updateContext(signal, data)

    # Add trigger and notification info
    if notification:
        data['notification']['name'] = notification.titleOrId()
    if guidManager:
        trigger = guidManager.getObject(signal.trigger_uuid)
        if trigger:
            data['trigger']['name'] = trigger.titleOrId()

    return data


def _getBaseUrl(zopeurl):
    if not zopeurl:
        zopeurl = Utils.getDefaultZopeUrl()
    return '%s/zport/dmd' % zopeurl


def _getBaseEventUrl(zopeurl):
    return '%s/Events' % _getBaseUrl(zopeurl)


def _getBaseDeviceUrl(zopeurl, device_class, device_name):
    """
    Builds the URL for a device.
    Example: "http://.../Devices/Server/Linux/devices/localhost/devicedetail"
    """
    if device_class and device_name:
        # the device
        return '%s/Devices%s/devices/%s/devicedetail' % \
               (_getBaseUrl(zopeurl), device_class, device_name)
    else:
        # unknown device, just link to infrastructure page
        return "%s/itinfrastructure" % _getBaseUrl(zopeurl)


def getEventUrl(zopeurl, evid):
    return "%s/viewDetail?evid=%s" % (_getBaseEventUrl(zopeurl), evid)


def getEventsUrl(zopeurl, device_class=None, device_name=None):
    if device_class and device_name:
        # events for a specific device
        return "%s#deviceDetailNav:device_events" % _getBaseDeviceUrl(zopeurl, device_class, device_name)
    else:
        #events on all devices
        return "%s/Events/evconsole" % _getBaseUrl(zopeurl)


def getAckUrl(zopeurl, evid):
    return "%s/manage_ackEvents?evids=%s&zenScreenName=viewEvents" %\
           (_getBaseEventUrl(zopeurl), evid)


def getCloseUrl(zopeurl, evid):
    return "%s/manage_deleteEvents?evids=%s&zenScreenName=viewHistoryEvents" %\
           (_getBaseEventUrl(zopeurl), evid)


def getReopenUrl(zopeurl, evid):
    return "%s/manage_undeleteEvents?evids=%s&zenScreenName=viewEvents" %\
           (_getBaseEventUrl(zopeurl), evid)


class IActionBase(object):
    """
    Mixin class for provided some common, necessary, methods.
    """

    def configure(self, options):
        self.options = options

    def getInfo(self, notification):
        return self.actionContentInfo(notification)

    def generateJavascriptContent(self, notification):
        content = self.getInfo(notification)
        return IFormBuilder(content).render(fieldsets=False)

    def getDefaultData(self, dmd):
        return {}


class TargetableAction(object):
    
    shouldExecuteInBatch = False

    def setupAction(self, dmd):
        """
        Some actions need to configure themselves with properties from the dmd.
        This is their opportunity to do so.
        """
        pass

    def getTargets(self, notification):
        targets = set()
        for recipient in notification.recipients:
            if recipient['type'] in ['group', 'user']:
                guid = recipient['value']
                target_obj = self.guidManager.getObject(guid)
                if target_obj:
                    for target in self.getActionableTargets(target_obj):
                        targets.add(target)
            else:
                targets.add(recipient['value'])
        return targets
    
    def handleExecuteError(self, exception, notification, target):
        # If there is an error executing this action on a target,
        # we need to handle it, but we don't want to prevent other
        # actions from executing on any other targets that may be
        # about to be acted on.
        msg = 'Error executing action {notification} on {target}'.format(
            notification=notification.id,
            target=target,
        )
        log.error(exception)
        log.error(msg)
        traceback = format_exc()
        event = Event(device="localhost",
                      eventClass="/App/Failed",
                      summary=msg,
                      message=traceback,
                      severity=SEV_WARNING, component="zenactiond")
        notification.dmd.ZenEventManager.sendEvent(event)

    
    def executeBatch(self, notification, signal, targets):
        raise NotImplemented()


    def execute(self, notification, signal):
        self.setupAction(notification.dmd)

        exceptionTargets = []
        targets = self.getTargets(notification)
        if self.shouldExecuteInBatch:
            try:
                log.debug("Executing batch action for targets.")
                self.executeBatch(notification, signal, targets)
            except Exception, e:
                self.handleExecuteError(e, notification, targets)
                exceptionTargets.extend(targets)
        else:
            log.debug("Executing action serially for targets.")
            for target in targets:
                try:
                    self.executeOnTarget(notification, signal, target)
                    log.debug('Done executing action for target: %s' % target)
                except Exception, e:
                    self.handleExecuteError(e, notification, target)
                    exceptionTargets.append(target)

        if exceptionTargets:
            raise TargetableActionException(self, notification, exceptionTargets)

class EmailAction(IActionBase, TargetableAction):
    implements(IAction)
    id = 'email'
    name = 'Email'
    actionContentInfo = IEmailActionContentInfo
    
    shouldExecuteInBatch = True
    
    def __init__(self):
        super(EmailAction, self).__init__()

    def getDefaultData(self, dmd):
        return dict(host=dmd.smtpHost,
                    port=dmd.smtpPort,
                    user=dmd.smtpUser,
                    password=dmd.smtpPass,
                    useTls=dmd.smtpUseTLS,
                    email_from=dmd.getEmailFrom())

    def setupAction(self, dmd):
        self.guidManager = GUIDManager(dmd)

    def _encodeBody(self, body):
        """
        Try to encode the text in the following character sets, if we can't decode it
        then strip out anything we can't encode in ascii.
        """        
        for body_charset in 'US-ASCII', 'ISO-8859-1', 'UTF-8':
            try:
                plain_body = MIMEText(body.encode(body_charset), 'plain', body_charset)
                break
            except UnicodeError:
                pass                
        else:            
            plain_body = MIMEText(body.decode('ascii', 'ignore'))
        return plain_body
    
    def executeBatch(self, notification, signal, targets):
        self.setupAction(notification.dmd)

        data = _signalToContextDict(signal, self.options.get('zopeurl'), notification, self.guidManager)

        # Check for email recipients in the event
        details = data['evt'].details
        mail_targets = details.get('recipients', '')
        mail_targets = [x.strip() for x in mail_targets.split(',') if x.strip()]
        if len(mail_targets) > 0:
            log.debug("Adding recipients defined in the event %s", mail_targets)
            targets |= set(mail_targets)

        log.debug("Executing %s action for targets: %s", self.name, targets)

        if signal.clear:
            log.debug('This is a clearing signal.')
            subject = processTalSource(notification.content['clear_subject_format'], **data)
            body = processTalSource(notification.content['clear_body_format'], **data)
        else:
            subject = processTalSource(notification.content['subject_format'], **data)
            body = processTalSource(notification.content['body_format'], **data)

        log.debug('Sending this subject: %s' % subject)
        log.debug('Sending this body: %s' % body)
        body = self._stripTags(body)
        plain_body = self._encodeBody(body)
            
        email_message = plain_body

        if notification.content['body_content_type'] == 'html':
            email_message = MIMEMultipart('related')
            email_message_alternative = MIMEMultipart('alternative')
            email_message_alternative.attach(plain_body)

            html_body = self._encodeBody(body.replace('\n', '<br />\n'))
            html_body.set_type('text/html')
            email_message_alternative.attach(html_body)

            email_message.attach(email_message_alternative)

        host = notification.content['host']
        port = notification.content['port']
        user = notification.content['user']
        password = notification.content['password']
        useTls = notification.content['useTls']
        email_from = notification.content['email_from']

        email_message['Subject'] = subject
        email_message['From'] = email_from
        email_message['To'] = ','.join(targets)
        email_message['Date'] = formatdate(None, True)

        result, errorMsg = sendEmail(
            email_message,
            host, port,
            useTls,
            user, password
        )

        if result:
            log.debug("Notification '%s' sent emails to: %s",
                     notification.id, targets)
        else:
            raise ActionExecutionException(
                "Notification '%s' FAILED to send emails to %s: %s" %
                (notification.id, targets, errorMsg)
            )

    def getActionableTargets(self, target):
        """
        @param target: This is an object that implements the IProvidesEmailAddresses
            interface.
        @type target: UserSettings or GroupSettings.
        """
        if IProvidesEmailAddresses.providedBy(target):
            return target.getEmailAddresses()

    def _stripTags(self, data):
        """A quick html => plaintext converter
           that retains and displays anchor hrefs

           stolen from the old zenactions.
           @todo: needs to be updated for the new data structure?
        """
        tags = re.compile(r'<(.|\n)+?>', re.I | re.M)
        aattrs = re.compile(r'<a(.|\n)+?href=["\']([^"\']*)[^>]*?>([^<>]*?)</a>', re.I | re.M)
        anchors = re.finditer(aattrs, data)
        for x in anchors: data = data.replace(x.group(), "%s: %s" % (x.groups()[2], x.groups()[1]))
        data = re.sub(tags, '', data)
        return data

    def updateContent(self, content=None, data=None):
        updates = dict()
        updates['body_content_type'] = data.get('body_content_type', 'html')

        properties = ['subject_format', 'body_format', 'clear_subject_format', 'clear_body_format']
        properties.extend(['host', 'port', 'user', 'password', 'useTls', 'email_from'])
        for k in properties:
            updates[k] = data.get(k)

        content.update(updates)


class PageAction(IActionBase, TargetableAction):
    implements(IAction)

    id = 'page'
    name = 'Page'
    actionContentInfo = IPageActionContentInfo

    def __init__(self):
        super(PageAction, self).__init__()

    def setupAction(self, dmd):
        self.guidManager = GUIDManager(dmd)
        self.page_command = dmd.pageCommand

    def executeOnTarget(self, notification, signal, target):
        """
        @TODO: handle the deferred parameter on the sendPage call.
        """
        log.debug('Executing action: Page')

        data = _signalToContextDict(signal, self.options.get('zopeurl'), notification, self.guidManager)
        if signal.clear:
            log.debug('This is a clearing signal.')
            subject = processTalSource(notification.content['clear_subject_format'], **data)
        else:
            subject = processTalSource(notification.content['subject_format'], **data)

        success, errorMsg = Utils.sendPage(
            target, subject, self.page_command,
            #deferred=self.options.cycle)
            deferred=False)

        if success:
            log.debug("Notification '%s' sent page to %s." % (notification, target))
        else:
            raise ActionExecutionException(
                "Notification '%s' failed to send page to %s. (%s)" % (notification, target, errorMsg))

    def getActionableTargets(self, target):
        """
        @param target: This is an object that implements the IProvidesPagerAddresses
            interface.
        @type target: UserSettings or GroupSettings.
        """
        if IProvidesPagerAddresses.providedBy(target):
            return target.getPagerAddresses()

    def updateContent(self, content=None, data=None):
        updates = dict()

        properties = ['subject_format', 'clear_subject_format', ]
        for k in properties:
            updates[k] = data.get(k)

        content.update(updates)


class EventCommandProtocol(ProcessProtocol):
    def __init__(self, cmd):
        self.cmd = cmd
        self.data = ''
        self.error = ''

    def timedOut(self, value):
        log.error("Command '%s' timed out" % self.cmd.id)
        # FIXME: send an event or something?
        return value

    def processEnded(self, reason):
        log.debug("Command finished: '%s'" % reason.getErrorMessage())

        # FIXME: send an event or something?
        #
        # code = 1
        # try:
        #     code = reason.value.exitCode
        # except AttributeError:
        #     pass
        # code = reason.value.exitCode
        # if code == 0:
        #     cmdData = self.data or "<command produced no output>"
        # else:
        #     cmdError = self.error or "<command produced no output>"

    def outReceived(self, text):
        self.data += text

    def errReceived(self, text):
        self.error += text


class CommandAction(IActionBase, TargetableAction):
    implements(IAction)

    id = 'command'
    name = 'Command'
    actionContentInfo = ICommandActionContentInfo

    shouldExecuteInBatch = False

    def configure(self, options):
        super(CommandAction, self).configure(options)
        self.processQueue = ProcessQueue(options.get('maxCommands', 10))
        self.processQueue.start()

    def setupAction(self, dmd):
        self.guidManager = GUIDManager(dmd)
        self.dmd = dmd

    def execute(self, notification, signal):
        # check to see if we have any targets
        if notification.recipients:
            return super(CommandAction, self).execute(notification, signal)
        else:
            self._execute(notification, signal)

    def executeOnTarget(self, notification, signal, target):
        log.debug('Executing command action: %s on %s', self.name, target)
        environ ={}
        environ['user'] = getattr(self.dmd.ZenUsers, target, None)
        self._execute(notification, signal, environ)

    def _execute(self, notification, signal, extra_env= {}):
        self.setupAction(notification.dmd)
        log.debug('Executing command action: %s', self.name)

        if signal.clear:
            command = notification.content['clear_body_format']
        else:
            command = notification.content['body_format']

        log.debug('Executing this command: %s', command)
        
        actor = signal.event.occurrence[0].actor
        device = None
        if actor.element_uuid:
            device = self.guidManager.getObject(actor.element_uuid)

        component = None
        if actor.element_sub_uuid:
            component = self.guidManager.getObject(actor.element_sub_uuid)

        user_env_format = notification.content.get('user_env_format', '')
        env = dict( envvar.split('=') for envvar in user_env_format.split(';') if '=' in envvar)
        environ = {'dev': device, 'component': component, 'dmd': notification.dmd, 'env': env}
        data = _signalToContextDict(signal, self.options.get('zopeurl'), notification, self.guidManager)
        environ.update(data)

        if environ.get('evt', None):
            environ['evt'] = self._escapeEvent(environ['evt'])
        if environ.get('clearEvt', None):
            environ['clearEvt'] = self._escapeEvent(environ['clearEvt'])
        environ.update(extra_env)
        try:
            command = processTalSource(command, **environ)
        except Exception:
            raise ActionExecutionException('Unable to perform TALES evaluation on "%s" -- is there an unescaped $?' % command)

        log.debug('Executing this compiled command: "%s"' % command)
        _protocol = EventCommandProtocol(command)

        log.debug('Queueing up command action process.')
        self.processQueue.queueProcess(
            '/bin/sh',
                ('/bin/sh', '-c', command),
            env=environ['env'],
            processProtocol=_protocol,
            timeout=int(notification.content['action_timeout']),
            timeout_callback=_protocol.timedOut
        )

    def getActionableTargets(self, target):
        ids = [target.id]
        if isinstance(target, GroupSettings):
            ids = [x.id for x in target.getMemberUserSettings()]
        return ids

    def updateContent(self, content=None, data=None):
        updates = dict()

        properties = ['body_format', 'clear_body_format', 'action_timeout', 'user_env_format']
        for k in properties:
            updates[k] = data.get(k)

        content.update(updates)

    def _escapeEvent(self, evt):
        """
        Escapes the relavent fields of an event context for event commands.
        """
        if evt.message:
            evt.message = self._wrapInQuotes(evt.message)
        if evt.summary:
            evt.summary = self._wrapInQuotes(evt.summary)
        return evt

    def _wrapInQuotes(self, msg):
        """
        Wraps the message in quotes, escaping any existing quote.

        Before:  How do you pronounce "Zenoss"?
        After:  "How do you pronounce \"Zenoss\"?"
        """
        QUOTE = '"'
        BACKSLASH = '\\'
        return ''.join((QUOTE, msg.replace(QUOTE, BACKSLASH + QUOTE), QUOTE))

class SNMPTrapAction(IActionBase):
    implements(IAction)

    id = 'trap'
    name = 'SNMP Trap'
    actionContentInfo = ISnmpTrapActionContentInfo

    _sessions = {}

    def setupAction(self, dmd):
        self.guidManager = GUIDManager(dmd)

    def execute(self, notification, signal):
        """
        Send out an SNMP trap according to the definition in ZENOSS-MIB.
        """
        log.debug('Processing SNMP Trap action.')
        self.setupAction(notification.dmd)
        data = _signalToContextDict(signal, self.options.get('zopeurl'), notification, self.guidManager)

        # For clear signals we need to send the "clear" event first so the
        # receiver will be able to correlate the later "cleared" event's
        # evtClearId value.

        # Only send the "clear" event if it has a uuid. A clear signal will be
        # sent if a user closing an event, or if it's automatically aged.
        if signal.clear and data['clearEventSummary'].uuid:
            self._sendTrap(notification, data, data['clearEventSummary'])

        self._sendTrap(notification, data, data['eventSummary'])

    def _sendTrap(self, notification, data, event):
        actor = getattr(event, "actor", None)
        details = event.details
        baseOID = '1.3.6.1.4.1.14296.1.100'

        fields = {
           'uuid' :                         ( 1, event),
           'fingerprint' :                  ( 2, event),
           'element_identifier' :           ( 3, actor),
           'element_sub_identifier' :       ( 4, actor),
           'event_class' :                  ( 5, event),
           'event_key' :                    ( 6, event),
           'summary' :                      ( 7, event),
           'message' :                      ( 8, event),
           'severity' :                     ( 9, event),
           'status' :                       (10, event),
           'event_class_key' :              (11, event),
           'event_group' :                  (12, event),
           'state_change_time' :            (13, event),
           'first_seen_time' :              (14, event),
           'last_seen_time' :               (15, event),
           'count' :                        (16, event),
           'zenoss.device.production_state':(17, details),
           'agent':                         (20, event),
           'zenoss.device.device_class':    (21, details),
           'zenoss.device.location' :       (22, details),
           'zenoss.device.systems' :        (23, details),
           'zenoss.device.groups' :         (24, details),
           'zenoss.device.ip_address':      (25, details),
           'syslog_facility' :              (26, event),
           'syslog_priority' :              (27, event),
           'nt_event_code' :                (28, event),
           'current_user_name' :            (29, event),
           'cleared_by_event_uuid' :        (31, event),
           'zenoss.device.priority' :       (32, details),
           'event_class_mapping_uuid':      (33, event),
           'element_title':                 (34, actor),
           'element_sub_title':             (35, actor)
           }

        eventDict = self.createEventDict(fields, event)
        self.processEventDict(eventDict, data, notification.dmd)
        varbinds = self.makeVarBinds(baseOID, fields, eventDict)

        session = self._getSession(notification.content)
        
        for v in varbinds:
            log.debug(v)
        session.sendTrap(baseOID + '.0.0.1', varbinds=varbinds)

    def createEventDict(self, fields, event):
        """
        Create an event dictionary suitable for Python evaluation.
        """
        eventDict = {}
        for field, oidspec in fields.items():
            i, source = oidspec
            if source is event.details:
                val = source.get(field, '')
            else:
                val = getattr(source, field, '')
            eventDict[field] = val
        return eventDict

    def processEventDict(self, eventDict, data, dmd):
        """
        Integration hook
        """
        pass

    def makeVarBinds(self, baseOID, fields, eventDict):
        """
        Make the SNMP variable bindings in numeric order.
        """
        uintValues = (9, 10, 26, 27)
        varbinds = []
        for field, oidspec in sorted(fields.items(), key=lambda x: x[1][0]):
            i, source = oidspec
            val = eventDict.get(field, '')
            if isinstance(val, (list, tuple, set)):
                val = '|'.join(val)

            # Create the binding
            oid = "%s.%d" % (baseOID, i)
            oidType = 's' if i not in uintValues else 'u'
            # No matter what the OID data type, send in strings as that's what is expected
            val = str(val)

            varbinds.append( (oid, oidType, val) )
        return varbinds

    def updateContent(self, content=None, data=None):
        content['action_destination'] = data.get('action_destination')
        content['community'] = data.get('community')
        content['version'] = data.get('version')
        content['port'] = int(data.get('port'))

    def _getSession(self, content):
        traphost = content['action_destination']
        port = content.get('port', 162)
        destination = '%s:%s' % (traphost, port)

        if not traphost or port <= 0:
            log.error("%s: SNMP trap host information %s is incorrect ", destination)
            return None

        community = content.get('community', 'public')
        version = content.get('version', 'v2c')

        session = self._sessions.get(destination, None)
        if session is None:
            log.debug("Creating SNMP trap session to %s", destination)

            # Test that the hostname and port are sane.
            try:
                getaddrinfo(traphost, port)
            except Exception:
                raise ActionExecutionException("The destination %s is not resolvable." % destination)

            session = netsnmp.Session((
                '-%s' % version,
                '-c', community,
                destination)
            )
            session.open()
            self._sessions[destination] = session

        return session
