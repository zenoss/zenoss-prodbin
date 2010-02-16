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


import socket
import time
from sets import Set
import Globals

from ZODB.POSException import POSError
from _mysql_exceptions import OperationalError, ProgrammingError 

from Products.ZenUtils.ProcessQueue import ProcessQueue
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.ZenTales import talesCompile, getEngine
from Products.ZenEvents.Exceptions import ZenEventNotFound
from ZenEventClasses import App_Start, App_Stop, Status_Heartbeat 
from ZenEventClasses import Cmd_Fail
import Event
from Schedule import Schedule
from UpdateCheck import UpdateCheck
from Products.ZenUtils import Utils
from twisted.internet import reactor
from twisted.internet.protocol import ProcessProtocol
from email.Utils import formatdate

DEFAULT_MONITOR = "localhost"

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
    Take actions based on events in the event manager.
    Start off by sending emails and pages.
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
            except (SystemExit, KeyboardInterrupt, OperationalError, POSError):
                raise
            except:
                if self.lastCommand:
                    self.log.warning(self.lastCommand)
                self.log.exception("action:%s",ar.getId())

    def checkVersion(self, zem):
        self.updateCheck.check(self.dmd, zem)
        import transaction
        transaction.commit()

    def processEvent(self, zem, context, action):
        userFields = context.getEventFields()
        columnNames = self._columnNames('status')
        fields = [f for f in userFields if f in columnNames]
        userid = context.getUserid()
        # get new events
        nwhere = context.where.strip() or '1 = 1'
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
        q = ("SELECT monitor, component "
             "FROM status WHERE eventClass = '%s'" % Status_Heartbeat)
        heartbeatState = Set(self.query(q))
           
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
                            monitor=monitor,
                            severity=Event.Error))
            heartbeatState.discard((monitor, comp))

        # clear heartbeats
        for monitor, comp in heartbeatState:
            hostname = self.fetchMonitorHostname(monitor)
            self.sendEvent(
                Event.Event(device=hostname, component=comp, 
                            eventClass=Status_Heartbeat, 
                            summary="%s %s heartbeat clear" % (monitor, comp),
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


    def runCycle(self):
        try:
            start = time.time()
            self.syncdb()
            self.mainbody()
            self.log.info("processed %s rules in %.2f secs", 
                           len(self.actions), time.time()-start)
            self.sendHeartbeat()
        except:
            self.log.exception("unexpected exception")
        if self.options.cycle:
            reactor.callLater(self.options.cycletime, self.runCycle)
        else:
            def shutdown(value):
                reactor.stop()
                return value
            self.log.info("waiting for outstanding process to end")
            d = self._processQ.stop()
            d.addBoth(shutdown)


    def run(self):
        self.prodState = filter(lambda x: x.split(':')[0] == 'Production',
                                self.dmd.prodStateConversions)
        import socket
        self.daemonHostname = socket.getfqdn()
        self.monitorToHost = {}
        try:
            # eg ['Production:1000']
            self.prodState = int(self.prodState[0].split(':')[1])
        except:
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
            self.log.warning('failed to email %s on rule %s: %s',
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
                " events. Default is %s." % DEFAULT_MONITOR)
        self.parser.add_option("--parallel", dest="parallel",
            default=10, type='int',
            help="Number of event commands to run concurrently")


    def sigTerm(self, signum=None, frame=None):
        'controlled shutdown of main loop on interrupt'
        try:
            ZCmdBase.sigTerm(self, signum, frame)
        except SystemExit:
            reactor.stop()


class ZenActions(BaseZenActions, ZCmdBase):
    
    def __init__(self):
        ZCmdBase.__init__(self)
        self.schedule = Schedule(self.options, self.dmd)
        self.schedule.sendEvent = self.dmd.ZenEventManager.sendEvent
        self.schedule.monitor = self.options.monitor

        self.actions = []
        self.loadActionRules()
        self.updateCheck = UpdateCheck()
        self.sendEvent(Event.Event(device=self.options.monitor, 
                        eventClass=App_Start, 
                        summary="zenactions started",
                        severity=0, component="zenactions"))


if __name__ == "__main__":
    za = ZenActions()
    import logging
    logging.getLogger('zen.Events').setLevel(20)
    za.run()
