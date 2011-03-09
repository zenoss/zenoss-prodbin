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
from ZODB.POSException import ConflictError
from _mysql_exceptions import OperationalError

from twisted.internet import reactor

from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenEvents.Exceptions import MySQLConnectionError
from ZenEventClasses import App_Start, App_Stop, Status_Heartbeat
from Products.ZenEvents import Event
from Schedule import Schedule
from UpdateCheck import UpdateCheck
from Products.ZenUtils import Utils


DEFAULT_MONITOR = "localhost"

deviceFilterRegex = re.compile(r"Device\s(.*?)'(.*?)'", re.IGNORECASE)

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

class BaseZenActions(object):
    """
    This is a base class for unit testing.
    """
    lastCommand = None

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

    def query(self, stmt):
        """
        Execute stmt against ZenEventManager connection and fetch all results.
        """
        def callback(cursor, **unused):
            return cursor.fetchall()
        return self._getCursor(stmt, callback)


    def checkVersion(self, zem):
        self.updateCheck.check(self.dmd, zem)
        import transaction
        transaction.commit()


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

    def mainbody(self):
        """main loop to run actions.
        """
        from twisted.internet.process import reapAllProcesses
        reapAllProcesses()
        zem = self.dmd.ZenEventManager
        self.checkVersion(zem)
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

        def startup():
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


