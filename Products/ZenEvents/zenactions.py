###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2009 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
#! /usr/bin/env python

__doc__='''zenactions

Turn events into notifications (pages, emails).

'''

import re
import socket
import time
import signal
from email.Utils import formatdate

import Globals
from ZODB.POSException import POSError, ConflictError
from _mysql_exceptions import OperationalError, ProgrammingError

from twisted.internet import reactor
from twisted.internet.protocol import ProcessProtocol

from Products.ZenUtils.ProcessQueue import ProcessQueue
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.ZenTales import talesCompile, getEngine
from Products.ZenEvents.Exceptions import ZenEventNotFound, MySQLConnectionError
from ZenEventClasses import App_Start, App_Stop, Status_Heartbeat
from ZenEventClasses import Cmd_Fail
from Products.ZenEvents import Event
from Schedule import Schedule
from UpdateCheck import UpdateCheck
from Products.ZenUtils import Utils


DEFAULT_MONITOR = "localhost"

deviceFilterRegex = re.compile("Device\s(.*?)'(.*?)'", re.IGNORECASE)

# Panic handling stuff
START_PANIC_THRESHOLD = 3
START_PANIC_SLEEP = 60
RUN_PANIC_THRESHOLD = 0
RUN_PANIC_SLEEP = 60
DEFAULT_ZEO_CHECK_TIMEOUT = 60

MYSQL_PANIC_MESSAGE = "Encountered a MySQL connection error."
ZEO_PANIC_MESSAGE = "Encountered a ZEO connection error."
GENERIC_PANIC_MESSAGE = "Encountered an unexpected error."

class ZeoWatcher(Exception):
    pass


def _capitalize(s):
    return s[0:1].upper() + s[1:]

class EventCommandProtocol(ProcessProtocol):

    def __init__(self, cmd, server):
        self.cmd = cmd
        self.server = server
        self.data = ''
        self.error = ''

    def timedOut(self, value):
        self.server.log.error("Command %s timed out" % self.cmd.id)
        self.server.sendEvent(Event.Event(
            device=self.server.options.monitor,
            eventClass=Cmd_Fail,
            severity=Event.Error,
            component="zenactions",
            eventKey=self.cmd.id,
            summary="Timeout running %s" % (self.cmd.id,),
            ))
        return value

    def processEnded(self, reason):
        self.server.log.debug("Command finished: %s" % reason.getErrorMessage())
        code = 1
        try:
            code = reason.value.exitCode
        except AttributeError:
            pass

        if code == 0:
            cmdData = self.data or "<command produced no output>"
            self.server.log.debug("Command %s says: %s", self.cmd.id, cmdData)
            self.server.sendEvent(Event.Event(
                device=self.server.options.monitor,
                eventClass=Cmd_Fail,
                severity=Event.Clear,
                component="zenactions",
                eventKey=self.cmd.id,
                summary="Command succeeded: %s: %s" % (
                    self.cmd.id, cmdData),
                ))
        else:
            cmdError = self.error or "<command produced no output>"
            self.server.log.error("Command %s says %s", self.cmd.id, cmdError)
            self.server.sendEvent(Event.Event(
                device=self.server.options.monitor,
                eventClass=Cmd_Fail,
                severity=Event.Error,
                component="zenactions",
                eventKey=self.cmd.id,
                summary="Error running: %s: %s" % (
                    self.cmd.id, cmdError),
                ))

    def outReceived(self, text):
        self.data += text

    def errReceived(self, text):
        self.error += text


class BaseZenActions(object):
    """
    This is a base class for unit testing.
    """
    lastCommand = None

    addstate = ("INSERT INTO alert_state "
                "VALUES ('%s', '%s', '%s', NULL) "
                "ON DUPLICATE KEY UPDATE lastSent = now()")


    clearstate = ("DELETE FROM alert_state "
                  " WHERE evid='%s' "
                  "   AND userid='%s' "
                  "   AND rule='%s'")

#FIXME attempt to convert subquery to left join that doesn't work
#    newsel = """select %s, evid from status s left join alert_state a
#                on s.evid=a.evid where a.evid is null and
#                a.userid='%s' and a.rule='%s'"""

    newsel = ("SELECT %s, evid FROM status WHERE "
              "%s AND evid NOT IN "
              " (SELECT evid FROM alert_state "
              "  WHERE userid='%s' AND rule='%s' %s)")

    clearsel = ("SELECT %s, h.evid FROM history h, alert_state a "
                " WHERE h.evid=a.evid AND a.userid='%s' AND a.rule='%s'")

    clearEventSelect = ("SELECT %s "
                        "  FROM history clear, history event "
                        " WHERE clear.evid = event.clearid "
                        "   AND event.evid = '%s'")

    def loadActionRules(self):
        """Load the ActionRules into the system.
        """
        self.actions = []
        for ar in self.dmd.ZenUsers.getAllActionRules():
            if not ar.enabled: continue
            userid = ar.getUser().id
            self.actions.append(ar)
            self.log.debug("action:%s for:%s loaded", ar.getId(), userid)


    def _getCursor(self, stmt, callback):
        """
        Get a cursor for the ZenEventManager connection.  Execute statement
        and call the callback with the cursor and number of row affected.
        """
        result = None
        self.lastCommand = stmt
        self.log.debug(stmt)
        zem = self.dmd.ZenEventManager
        conn = zem.connect()
        try:
            curs = conn.cursor()
            rowsAffected = curs.execute(stmt)
            result = callback(cursor=curs, rowsAffected=rowsAffected)
        finally:
            zem.close(conn)
        return result


    def execute(self, stmt):
        """
        Execute stmt against ZenEventManager connection and return the number
        of rows that were affected.
        """
        def callback(rowsAffected, **unused):
            return rowsAffected
        return self._getCursor(stmt, callback)


    def query(self, stmt):
        """
        Execute stmt against ZenEventManager connection and fetch all results.
        """
        def callback(cursor, **unused):
            return cursor.fetchall()
        return self._getCursor(stmt, callback)


    def _describe(self, stmt):
        """
        Execute stmt against ZenEventManager connection and return the cursor
        description.
        """
        def callback(cursor, **unused):
            return cursor.description
        return self._getCursor(stmt, callback)


    def _columnNames(self, table):
        """
        Returns the column names for the table using a ZenEventManager
        connection.
        """
        description = self._describe("SELECT * FROM %s LIMIT 0" % table)
        return [d[0] for d in description]


    def getBaseUrl(self, device=None):
        url = self.options.zopeurl
        if device:
            return "%s%s" % (url, device.getPrimaryUrlPath())
        else:
            return "%s/zport/dmd/Events" % (url)


    def getEventUrl(self, evid, device=None):
        return "%s/viewDetail?evid=%s" % (self.getBaseUrl(device), evid)


    def getEventsUrl(self, device=None):
        return "%s/viewEvents" % self.getBaseUrl(device)


    def getAckUrl(self, evid, device=None):
        return "%s/manage_ackEvents?evids=%s&zenScreenName=viewEvents" % (
            self.getBaseUrl(device), evid)


    def getDeleteUrl(self, evid, device=None):
        return "%s/manage_deleteEvents?evids=%s" % (
            self.getBaseUrl(device), evid) + \
            "&zenScreenName=viewHistoryEvents"


    def getUndeleteUrl(self, evid, device=None):
        return "%s/manage_undeleteEvents?evids=%s" % (
            self.getBaseUrl(device), evid) + \
            "&zenScreenName=viewEvents"


    def processRules(self, zem):
        """Run through all rules matching them against events.
        """
        for ar in self.actions:
            try:
                self.lastCommand = None
                # call sendPage or sendEmail
                actfunc = getattr(self, "send"+ar.action.title())
                self.processEvent(zem, ar, actfunc)
            except (ConflictError), ex:
                raise
            except (OperationalError, POSError), ex:
                raise
            except Exception:
                if self.lastCommand:
                    self.log.warning(self.lastCommand)
                self.log.exception("action:%s",ar.getId())

    def checkVersion(self, zem):
        self.updateCheck.check(self.dmd, zem)
        import transaction
        transaction.commit()

    def filterDeviceName(self, zem, whereClause):
        """This is somewhat janky but we only store the device id in the mysql
        database but allow people to search based on the device "title".
        This method resolves the disparity by searching the catalog first and using
        those results.
        """
        # they are not searching based on device at all
        if not 'device' in whereClause:
            return whereClause
        matches = deviceFilterRegex.findall(whereClause)

        # incase our awesome regex fails
        if not matches:
            return whereClause

        # get the devices from the event manager
        deviceids = []
        include = 'IN'

        # should be of the form "LIKE '%bar%'" or "NOT LIKE '%bar%'"
        for match in matches:
            operator = match[0]
            searchTerm = match[-1]
            originalDeviceFilter = operator + "'" + searchTerm + "'"

            # take care of begins with and ends with
            if searchTerm.startswith('%'):
                searchTerm = '.*' + searchTerm
            if searchTerm.endswith('%'):
                searchTerm = searchTerm + '.*'

            # search the catalog
            deviceids = zem._getDeviceIdsMatching(searchTerm.replace("%", ""), globSearch=False)

            # if we didn't find anything in the catalog just search the mysql
            if not deviceids:
                continue

            if not operator.lower().strip() in ('like', '='):
                include = 'NOT IN'
            deviceFilter = " %s ('%s') " % (include, "','".join(deviceids))
            whereClause = whereClause.replace(originalDeviceFilter, deviceFilter)

        return whereClause


    def processEvent(self, zem, context, action):
        userFields = context.getEventFields()
        columnNames = self._columnNames('status')
        fields = [f for f in userFields if f in columnNames]
        userid = context.getUserid()
        # get new events
        nwhere = context.where.strip() or '1 = 1'
        nwhere = self.filterDeviceName(zem, nwhere)
        if context.delay > 0:
            nwhere += " and firstTime + %s < UNIX_TIMESTAMP()" % context.delay
        awhere = ''
        if context.repeatTime:
            awhere += ' and DATE_ADD(lastSent, INTERVAL %d SECOND) > now() ' % (
                context.repeatTime,)
        q = self.newsel % (",".join(fields), nwhere, userid, context.getId(),
                           awhere)
        for result in self.query(q):
            evid = result[-1]
            data = dict(zip(fields, map(zem.convert, fields, result[:-1])))

            # Make details available to event commands.  zem.getEventDetail
            # uses the status table (which is where this event came from
            try:
                details = dict( zem.getEventDetail(evid).getEventDetails() )
                data.update( details )
            except ZenEventNotFound:
                pass

            device = self.dmd.Devices.findDevice(data.get('device', None))
            data['eventUrl'] = self.getEventUrl(evid, device)
            if device:
                data['eventsUrl'] = self.getEventsUrl(device)
                data['device'] = device.titleOrId()
            else:
                data['eventsUrl'] = 'n/a'
                data['device'] = data.get('device', None) or ''
            data['ackUrl'] = self.getAckUrl(evid, device)
            data['deleteUrl'] = self.getDeleteUrl(evid, device)
            severity = data.get('severity', -1)
            data['severityString'] = zem.getSeverityString(severity)
            if action(context, data, False):
                addcmd = self.addstate % (evid, userid, context.getId())
                self.execute(addcmd)

        # get clear events
        historyFields = [("h.%s" % f) for f in fields]
        historyFields = ','.join(historyFields)
        q = self.clearsel % (historyFields, userid, context.getId())
        for result in self.query(q):
            evid = result[-1]
            data = dict(zip(fields, map(zem.convert, fields, result[:-1])))

            # For clear events we are using the history table, so get the event details
            # using the history table.
            try:
                details = dict( zem.getEventDetailFromStatusOrHistory(evid).getEventDetails() )
                data.update( details )
            except ZenEventNotFound:
                pass

            # get clear columns
            cfields = [('clear.%s' % x) for x in fields]
            q = self.clearEventSelect % (",".join(cfields), evid)

            # convert clear columns to clear names
            cfields = [('clear%s' % _capitalize(x)) for x in fields]

            # there might not be a clear event, so set empty defaults
            data.update({}.fromkeys(cfields, ""))

            # pull in the clear event data
            for values in self.query(q):
                values = map(zem.convert, fields, values)
                data.update(dict(zip(cfields, values)))

            # If our event has a clearid, but we have no clear data it means
            # that we're in a small delay before it is inserted. We'll wait
            # until next time to deal with the clear.
            if data.get('clearid', None) and not data.get('clearEvid', None):
                continue

            data['clearOrEventSummary'] = (
                data['clearSummary'] or data['summary'])

            # We want to insert the ownerid and stateChange fields into the
            # clearSummary and clearFirstTime fields in the case where an
            # event was manually cleared by an operator.
            if not data.get('clearSummary', False) \
                and data.get('ownerid', False):
                data['clearSummary'] = data['ownerid']
                data['clearFirstTime'] = data.get('stateChange', '')

            # add in the link to the url
            device = self.dmd.Devices.findDevice(data.get('device', None))
            data['eventUrl'] = self.getEventUrl(evid, device)
            data['undeleteUrl'] = self.getUndeleteUrl(evid, device)
            severity = data.get('severity', -1)
            data['severityString'] = zem.getSeverityString(severity)
            # set the device title
            if device:
                data['device'] = device.titleOrId()
            delcmd = self.clearstate % (evid, userid, context.getId())
            if getattr(context, 'sendClear', True):
                if action(context, data, True):
                    self.execute(delcmd)
            else:
                self.execute(delcmd)


    def maintenance(self, zem):
        """Run stored procedures that maintain the events database.
        """
        sql = 'call age_events(%s, %s);' % (
                zem.eventAgingHours, zem.eventAgingSeverity)
        try:
            self.execute(sql)
        except ProgrammingError:
            self.log.exception("problem with proc: '%s'" % sql)


    def deleteHistoricalEvents(self, deferred=False, force=False):
        """
        Once per day delete events from history table.
        If force then run the deletion statement regardless of when it was
        last run (the deletion will still not run if the historyMaxAgeDays
        setting in the event manager is not greater than zero.)
        If deferred then we are running in a twisted reactor.  Run the
        deletion script in a non-blocking manner (if it is to be run) and
        return a deferred (if the deletion script is run.)
        In all cases return None if the deletion script is not run.
        """
        import datetime
        import os
        import twisted.internet.utils
        import Products.ZenUtils.Utils as Utils
        import transaction
        import subprocess

        def onSuccess(unused, startTime):
            self.log.info('Done deleting historical events in %.2f seconds' %
                            (time.time() - startTime))
            return None
        def onError(error, startTime):
            self.log.error('Error deleting historical events after '
                            '%s seconds: %s' % (time.time()-startTime,
                            error))
            return None

        # d is the return value.  It is a deferred if the deferred argument
        # is true and if we run the deletion script.  Otherwise it is None
        d = None

        # Unless the event manager has a positive number of days for its
        # historyMaxAgeDays setting then there is never any point in
        # performing the deletion.
        try:
            maxDays = int(self.dmd.ZenEventManager.historyMaxAgeDays)
        except ValueError:
            maxDays = 0
        if maxDays > 0:
            # lastDeleteHistoricalEvents_datetime is when the deletion
            # script was last run
            lastRun = getattr(self.dmd,
                                'lastDeleteHistoricalEvents_datetime', None)
            # lastDeleteHistoricalEvents_days is the value of historyMaxAgeDays
            # the last time the deletion script was run.  If this value has
            # changed then we run the script again regardless of when it was
            # last run.
            lastAge = getattr(self.dmd,
                                'lastDeleteHistoricalEvents_days', None)
            now = datetime.datetime.now()
            if not lastRun \
                    or now - lastRun > datetime.timedelta(1) \
                    or lastAge != maxDays \
                    or force:
                self.log.info('Deleting historical events older than %s days' %
                                maxDays)
                startTime = time.time()
                cmd = Utils.zenPath('Products', 'ZenUtils',
                                        'ZenDeleteHistory.py')
                args = ['--numDays=%s' % maxDays]
                if deferred:
                    # We're in a twisted reactor, so make a twisty call
                    d = twisted.internet.utils.getProcessOutput(
                            cmd, args, os.environ, errortoo=True)
                    d.addCallback(onSuccess, startTime)
                    d.addErrback(onError, startTime)
                else:
                    # Not in a reactor, so do this in a blocking manner
                    proc = subprocess.Popen(
                            [cmd]+args, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, env=os.environ)
                    # Trying to mimic how twisted returns results to us
                    # sort of.
                    output, _ = proc.communicate()
                    code = proc.wait()
                    if code:
                        onError(output, startTime)
                    else:
                        onSuccess(output, startTime)
                # Record circumstances of this run
                self.dmd.lastDeleteHistoricalEvents_datetime = now
                self.dmd.lastDeleteHistoricalEvents_days = maxDays
                transaction.commit()
        return d


    def fetchMonitorHostname(self, monitor='localhost'):
        if monitor in self.monitorToHost:
            return self.monitorToHost[monitor]

        all_monitors = self.dmd.Monitors.getPerformanceMonitorNames()
        if monitor in all_monitors:
            perfMonitor = self.dmd.Monitors.getPerformanceMonitor(monitor)
            hostname = getattr(perfMonitor, 'hostname', monitor)
        else:
            # Someone's put in something that we don't expect
            hostname = monitor

        if hostname == 'localhost':
            hostname = self.daemonHostname

        self.monitorToHost[monitor] = hostname
        return hostname

    def heartbeatEvents(self):
        """Create events for failed heartbeats.
        """
        # build cache of existing heartbeat issues
        q = ("SELECT device, component "
             "FROM status WHERE eventClass = '%s'" % Status_Heartbeat)
        heartbeatState = set(self.query(q))

        # Find current heartbeat failures
        # Note: 'device' in the heartbeat table is actually filled with the
        #        collector name
        sel = "SELECT device, component FROM heartbeat "
        sel += "WHERE DATE_ADD(lastTime, INTERVAL timeout SECOND) <= NOW();"
        for monitor, comp in self.query(sel):
            hostname = self.fetchMonitorHostname(monitor)
            self.sendEvent(
                Event.Event(device=hostname, component=comp,
                            eventClass=Status_Heartbeat,
                            summary="%s %s heartbeat failure" % (monitor, comp),
                            prodState=self.prodState,
                            severity=Event.Error))
            heartbeatState.discard((hostname, comp))

        # clear heartbeats
        for monitor, comp in heartbeatState:
            hostname = self.fetchMonitorHostname(monitor)
            self.sendEvent(
                Event.Event(device=hostname, component=comp,
                            eventClass=Status_Heartbeat,
                            summary="%s %s heartbeat clear" % (monitor, comp),
                            prodState=self.prodState,
                            severity=Event.Clear))

    def runEventCommand(self, cmd, data, clear = None):
        try:
            command = cmd.command
            if clear:
                command = cmd.clearCommand
            if not command:
                return True;
            device = self.dmd.Devices.findDevice(data.get('device', ''))
            component = None
            if device:
                componentName = data.get('component')
                for c in device.getMonitoredComponents():
                    if c.id == componentName:
                        component = c
                        break
            compiled = talesCompile('string:' + command)
            environ = {'dev':device, 'component':component, 'evt':data }
            res = compiled(getEngine().getContext(environ))
            if isinstance(res, Exception):
                raise res
            prot = EventCommandProtocol(cmd, self)
            if res:
                self.log.info('Queueing %s' % res)
                self._processQ.queueProcess('/bin/sh', ('/bin/sh', '-c', res),
                                        env=None, processProtocol=prot,
                                        timeout=cmd.defaultTimeout,
                                        timeout_callback=prot.timedOut)
        except Exception:
            self.log.exception('Error running command %s', cmd.id)
        return True


    def eventCommands(self, zem):
        now = time.time()
        count = 0
        for command in zem.commands():
            if command.enabled:
                count += 1
                self.processEvent(zem, command, self.runEventCommand)
        self.log.info("Processed %d commands in %f", count, time.time() - now)


    def mainbody(self):
        """main loop to run actions.
        """
        from twisted.internet.process import reapAllProcesses
        reapAllProcesses()
        zem = self.dmd.ZenEventManager
        self.loadActionRules()
        self.eventCommands(zem)
        self.processRules(zem)
        self.checkVersion(zem)
        self.maintenance(zem)
        self.deleteHistoricalEvents(deferred=self.options.cycle)
        self.heartbeatEvents()

    def run(self):
        self.prodState = filter(lambda x: x.split(':')[0] == 'Production',
                                self.dmd.prodStateConversions)
        import socket
        self.daemonHostname = socket.getfqdn()
        self.monitorToHost = {}
        try:
            # eg ['Production:1000']
            self.prodState = int(self.prodState[0].split(':')[1])
        except Exception:
            self.prodState = 1000

        self._processQ = ProcessQueue(self.options.parallel)
        def startup():
            self._processQ.start()
            self.schedule.start()
            self.runCycle()
        reactor.callWhenRunning(startup)
        reactor.run()

    def sendEvent(self, evt):
        """Send event to the system.
        """
        self.dmd.ZenEventManager.sendEvent(evt)


    def sendHeartbeat(self):
        """Send a heartbeat event for this monitor.
        """
        timeout = self.options.cycletime*3
        evt = Event.EventHeartbeat(self.options.monitor, "zenactions", timeout)
        self.sendEvent(evt)
        self.niceDoggie(self.options.cycletime)


    def stop(self):
        self.running = False
        self.log.info("stopping")
        self.sendEvent(Event.Event(device=self.options.monitor,
                        eventClass=App_Stop,
                        summary="zenactions stopped",
                        severity=3, component="zenactions"))

    def format(self, action, data, clear):
        fmt = action.format
        body = action.body
        if clear:
            fmt = action.clearFormat
            body = action.clearBody
        try:
            fmt = fmt % data
        except Exception, ex:
            fmt = "Error formatting event: %s" % (str(ex),)
        try:
            body = body % data
        except Exception, ex:
            body = "Error formatting event body: %s" % (str(ex),)
        return fmt, body

    def stripTags(self, data):
        """A quick html => plaintext converter
           that retains and displays anchor hrefs
        """
        import re
        tags = re.compile(r'<(.|\n)+?>', re.I|re.M)
        aattrs = re.compile(r'<a(.|\n)+?href=["\']([^"\']*)[^>]*?>([^<>]*?)</a>', re.I|re.M)
        anchors = re.finditer(aattrs, data)
        for x in anchors: data = data.replace(x.group(), "%s: %s" % (x.groups()[2], x.groups()[1]))
        data = re.sub(tags, '', data)
        return data

    def sendPage(self, action, data, clear = None):
        """Send and event to a pager.  Return True if we think page was sent,
        False otherwise.
        """
        if self.options.cycle and not reactor.running:
           # Give the reactor time to startup if necessary.
           return False

        fmt, body = self.format(action, data, clear)
        recipients = action.getAddresses()
        if not recipients:
            self.log.warning('failed to page %s on rule %s: %s',
                             action.getUser().id, action.id,
                             'Unspecified address.')
            return True

        result = False
        for recipient in recipients:
            success, errorMsg = Utils.sendPage(
                recipient, fmt, self.dmd.pageCommand,
                deferred=self.options.cycle)

            if success:
                self.log.info('sent page to %s: %s', recipient, fmt)
                # return True if anyone got the page
                result = result or success
            else:
                self.log.info('failed to send page to %s: %s %s',
                              recipient,
                              fmt,
                              errorMsg)
        return result

    def sendEmail(self, action, data, clear = None):
        """Send an event to an email address.
        Return True if we think the email was sent, False otherwise.
        """
        from email.MIMEText import MIMEText
        from email.MIMEMultipart import MIMEMultipart
        addr = action.getAddresses()
        if not addr:
            self.log.warning('Failed to email %s on rule %s: %s',
                action.getUser().id, action.id, 'Unspecified address.')
            return True

        fmt, htmlbody = self.format(action, data, clear)
        htmlbody = htmlbody.replace('\n','<br/>\n')
        body = self.stripTags(htmlbody)
        plaintext = MIMEText(body)

        emsg = None
        if action.plainText:
            emsg = plaintext
        else:
            emsg = MIMEMultipart('related')
            emsgAlternative = MIMEMultipart('alternative')
            emsg.attach( emsgAlternative )
            html = MIMEText(htmlbody)
            html.set_type('text/html')
            emsgAlternative.attach(plaintext)
            emsgAlternative.attach(html)

        emsg['Subject'] = fmt
        emsg['From'] = self.dmd.getEmailFrom()
        emsg['To'] = ', '.join(addr)
        emsg['Date'] = formatdate(None, True)
        result, errorMsg = Utils.sendEmail(emsg, self.dmd.smtpHost,
                    self.dmd.smtpPort, self.dmd.smtpUseTLS, self.dmd.smtpUser,
                    self.dmd.smtpPass)
        if result:
            self.log.info("rule '%s' sent email:%s to:%s",
                action.id, fmt, addr)
        else:
            self.log.info("rule '%s' failed to send email to %s: %s %s",
                action.id, ','.join(addr), fmt, errorMsg)
        return result


    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--cycletime',
            dest='cycletime', default=60, type="int",
            help="check events every cycletime seconds")
        self.parser.add_option(
            '--zopeurl', dest='zopeurl',
            default='http://%s:%d' % (socket.getfqdn(), 8080),
            help="http path to the root of the zope server")
        self.parser.add_option("--monitor", dest="monitor",
            default=DEFAULT_MONITOR,
            help="Name of monitor instance to use for heartbeat "
                " events. Default is %default.")
        self.parser.add_option("--parallel", dest="parallel",
            default=10, type='int',
            help="Number of event commands to run concurrently. Default: %default.")

    def sigTerm(self, signum=None, frame=None):
        'controlled shutdown of main loop on interrupt'
        try:
            ZCmdBase.sigTerm(self, signum, frame)
        except SystemExit:
            reactor.stop()

class ZenActions(BaseZenActions, ZCmdBase):
    """
    Take actions based on events in the event manager.
    Start off by sending emails and pages.
    """
    # BaseZenActions - unit testing
    # ZenActions - recovery-layer around BaseZenActions

    def __init__(self):
        # Replace Twisted's main loop to react more
        # appropriately to issues.
        reactor.wrappedMainLoop = reactor.mainLoop
        reactor.mainLoop = self.runtimeErrorWrapper
        self.connected = False
        self.startTime = time.time()
        self.startAttempts = 0
        self.runAttempts = 0
        self.mysqlproblem = False
        self.panicNotified = 0

        # Periodically check on ZEO connection status
        signal.signal(signal.SIGALRM, self.zeotimeoutHandler)
        signal.alarm(DEFAULT_ZEO_CHECK_TIMEOUT)

        while not self.connected:
            try:
                self.startAttempts += 1

                ZCmdBase.__init__(self)

                self.schedule = Schedule(self.options, self.dmd)
                self.schedule.sendEvent = self.dmd.ZenEventManager.sendEvent
                self.schedule.monitor = self.options.monitor

                self.actions = []
                self.loadActionRules()
                self.updateCheck = UpdateCheck()

                # Connect to MySQL and send startup event
                summaryDetails = ''
                if self.startAttempts > 1:
                    summaryDetails = ' (Startup attempts: %d, Time: %.2f)' % \
                        (self.startAttempts, time.time()-self.startTime)
                summary = "zenactions started %s" % summaryDetails
                event = Event.Event(device=self.options.monitor,
                                    eventClass=App_Start,
                                   summary=summary,
                                    severity=0, component="zenactions")
                self.sendEvent(event)

            # Note that we may (due to SIGALRM) get an exception
            # while we are processing an exception.
            except MySQLConnectionError, ex:
                try:
                    self.startupPanic(MYSQL_PANIC_MESSAGE, ex)
                    self.mysqlproblem = True
                except Exception, ex:
                    pass
            except OperationalError, ex:
                try:
                    self.startupPanic(MYSQL_PANIC_MESSAGE, ex)
                    # startupPanic initializes self.log for us
                    self.log.exception("Encountered MySQL error during startup")
                except Exception, ex:
                    pass
            except ZeoWatcher, ex:
                try:
                    self.startupPanic(ZEO_PANIC_MESSAGE, ex)
                except Exception, ex:
                    pass
            except Exception, ex:
                try:
                    self.startupPanic(GENERIC_PANIC_MESSAGE, ex)
                    # startupPanic initializes self.log for us
                    self.log.exception(GENERIC_PANIC_MESSAGE)
                except Exception, ex:
                    pass
            else:
                self.connected = True
                self.panicNotified = 0

    def buildOptions(self):
        BaseZenActions.buildOptions(self)
        self.parser.add_option("--paniccommand", dest="paniccommand",
            default='email', type='choice', choices=['email', 'page'],
            help="[ email | page ] Action to take in a panic condition. Default: %default")
        self.parser.add_option("--panictarget", dest="panictarget",
            default=None, type='str',
            help="The address (email or a pager number) to send the panic alert.")
        self.parser.add_option("--panichost", dest="panichost",
            default=None, type='str',
            help="This is the host to which email will be sent.")
        self.parser.add_option("--panicport", dest="panicport",
            default=25, type='int',
            help="This is the TCP/IP port to access Simple Mail Transport Protocol.")
        self.parser.add_option("--panicusetls", dest="panicusetls",
            default=False, action='store_true',
            help="Use Transport Layer Security for e-mail?")
        self.parser.add_option("--panicusername", dest="panicusername",
            default='', type='str',
            help="Use this only if authentication is required.")
        self.parser.add_option("--panicpassword", dest="panicpassword",
            default='', type='str',
            help="Use this only if authentication is required.")
        self.parser.add_option("--panicfromaddress", dest="panicfromaddress",
            default='root@localhost.localdomain', type='str',
            help="Defaults: '%default'.")
        self.parser.add_option("--panicmaxalerts", dest="panicmaxalerts",
            default=3, type='int',
            help="Max number of times to send out panic alerts." \
                 " Setting to 0 means send all alerts. (default: %default)")
        self.parser.add_option("--panicpagecommand", dest="panicpagecommand",
            default='$ZENHOME/bin/zensnpp localhost 444 $RECIPIENT', type='str',
            help="Paging command to send out panic page. (default: %default)")
        self.parser.add_option('--zeotimeout', dest="zeotimeout",
                    default=DEFAULT_ZEO_CHECK_TIMEOUT, type='int',
                    help="Amount of time to wait for zeo connections to die."\
                         " Default is %default")

    def runtimeErrorWrapper(self):
        """
        This is a replacement for Twisted's mainLoop code.
        The Twisted code tosses all of the errors and NEVER
        gives us a chance to do anything intelligent with the
        error conditions.
        """
        while reactor.running:
            try:
                # Advance simulation time in delayed event
                # processors.
                reactor.runUntilCurrent()
                t2 = reactor.timeout()
                t = reactor.running and t2
                reactor.doIteration(t)
            except (ConflictError), ex:
                self.log.error("Encountered ZODB conflict error at %s", ex)
            except (MySQLConnectionError, OperationalError), ex:
                self.mysqlproblem = True
                self.panic(MYSQL_PANIC_MESSAGE)
            except ZeoWatcher, ex:
                self.log.error("Encountered a zeo issue")
                self.panic(ZEO_PANIC_MESSAGE)
            except Exception, ex:
                self.log.error("Encountered an unknown issue")
                self.panic(GENERIC_PANIC_MESSAGE)

    def runCycle(self):
        """
        Periodically process commands and send out alerts.
        """
        if self.options.cycle:
            cycleDelay = self.options.cycletime

        try:
            start = time.time()
            self.syncdb()
            self.mainbody()
            self.log.info("Processed %s rules in %.2f secs",
                           len(self.actions), time.time()-start)
            self.sendHeartbeat()
            self.panicNotified = 0

        except (ConflictError), ex:
            self.log.error("Encountered ZODB conflict error at %s", ex)
        except (MySQLConnectionError, OperationalError), ex:
            cycleDelay = RUN_PANIC_SLEEP
            self.panic(MYSQL_PANIC_MESSAGE)

        except Exception, e:
            cycleDelay = RUN_PANIC_SLEEP
            self.panic(GENERIC_PANIC_MESSAGE)

        if self.options.cycle:
            reactor.callLater(cycleDelay, self.runCycle)
        else:
            def shutdown(value):
                reactor.stop()
                return value
            self.log.info("Waiting for outstanding process to end")
            d = self._processQ.stop()
            d.addBoth(shutdown)

    def panicPage(self, message):
        """
        When an error occurs, send out a distress call email.

        @parameter message: failure reason
        @type message: string
        """
        if not self.options.panictarget:
            self.log.warn('No alerts sent as --panictarget was not defined!')
            return

        for recipient in self.options.panictarget.split():
            success, errorMsg = Utils.sendPage(
                recipient, message, self.options.panicpagecommand,
                deferred=False)

            if success:
                self.log.info('Sent panic page to %s', recipient)
            else:
                self.log.info('Failed to send panic page to %s: %s',
                              recipient, errorMsg)

    def panicEmail(self, message):
        """
        When an error occurs, send out a distress call email.

        @parameter message: failure reason
        @type message: string
        """
        if not self.options.panictarget:
            self.log.warn('No alerts sent as --panictarget was not defined!')
            return

        if not self.options.panichost:
            self.log.warn('No alerts sent as --panichost was not defined!')
            return

        from email.MIMEText import MIMEText
        emsg = MIMEText("""
%s
The Zenoss zenactions daemon encountered a condtion where it was
not able to properly function.  This is generally due to either
not being able to connect to the ZODB database, or to MySQL.

On the Zenoss server, examine the $ZENHOME/log/zenactions.log
file to determine the root cause.  After resolving the issue,
restart Zenoss.
""" % message)

        host = self.options.panichost
        port = self.options.panicport
        addr = self.options.panictarget
        user = self.options.panicusername
        password = self.options.panicpassword
        useTLS = self.options.panicusetls

        emsg['Subject'] = "Zenoss zenactions daemon CRITICAL alert"
        emsg['From'] = self.options.panicfromaddress
        emsg['To'] = addr
        emsg['Date'] = formatdate(None, True)

        result, errorMsg = Utils.sendEmail(emsg, host,
                    port, useTLS, user, password)
        if result:
            self.log.info("Panic email sent email %s", addr)
        else:
            self.log.info("Panic email failed to send email to %s: %s",
                addr, errorMsg)

    def panic(self, message):
        """
        When an error occurs, send out a distress call to a pager or an email
        address.

        @parameter message: failure reason
        @type message: string
        """
        handler = {
            'email': self.panicEmail,
            'page': self.panicPage,
        }.get(self.options.paniccommand)

        # Limit the maximum number of alerts if desired
        if self.options.panicmaxalerts and \
           self.panicNotified >= self.options.panicmaxalerts:
            return

        if handler:
            handler(message)
        else:
            self.log.error("The --paniccommand flag '%s' is not recognized!",
                           self.options.paniccommand)
        self.panicNotified += 1

    def startupPanic(self, message, ex):
        """
        Initialization and retry logic for startup errors.

        @parameter message: failure reason
        @type message: string
        @parameter ex: exception used for reporting unknown errors
        @type ex: exception
        """
        if not hasattr(self, 'log'):
            from Products.ZenUtils.CmdBase import CmdBase
            CmdBase.__init__(self)

        self.log.debug('zenactions start attempt %s failure: %s',
                               self.startAttempts, str(ex))

        if self.startAttempts > START_PANIC_THRESHOLD:
            self.panic(message)

        self.log.debug('Sleeping %ds before trying again.',
                       START_PANIC_SLEEP)
        time.sleep(START_PANIC_SLEEP)

    def zeotimeoutHandler(self, signum=None, frame=None):
        """
        Supplying connection timeouts in ZCmd do NOT time out connections,
        so we need to resort to just bailing out if nothing interesting
        has occurred.
        We can't check the status of MySQL connections because we don't
        keep a persistent connection to the database.
        """
        # NB: This code may be called before basic initialization is done
        timeout = DEFAULT_ZEO_CHECK_TIMEOUT
        if hasattr(self, 'options'):
            timeout = self.options.zeotimeout

        signal.alarm(timeout)
        if not hasattr(self, 'db') or \
           not hasattr(self.db, 'storage') or\
           self.db.storage._closed:
            raise ZeoWatcher("ZEO is not connected!")

        # If we're okay, then reset the notification count
        if not self.mysqlproblem:
            self.panicNotified = 0


if __name__ == "__main__":
    za = ZenActions()
    import logging
    logging.getLogger('zen.Events').setLevel(20)
    za.run()


