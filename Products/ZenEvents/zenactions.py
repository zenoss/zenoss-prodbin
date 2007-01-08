#! /usr/bin/env python 
#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''zenactions

Turn events into notifications (pages, emails).

$Id$
'''

__version__ = "$Revision$"[11:-2]


import os
import socket
import time
from sets import Set
import Globals

from ZODB.POSException import POSError
from _mysql_exceptions import OperationalError, ProgrammingError 

from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.ZenTales import talesCompile, getEngine
from ZenEventClasses import AppStart, AppStop, HeartbeatStatus
import Event
from Schedule import Schedule
from UpdateCheck import UpdateCheck
import Products.ZenUtils.Utils as Utils
from twisted.internet import reactor
from twisted.internet.protocol import ProcessProtocol
from DateTime import DateTime

def _capitalize(s):
    return s[0:1].upper() + s[1:]

class EventCommandProtocol(ProcessProtocol):

    def __init__(self, cmd, server):
        self.cmd = cmd
        self.server = server
        self.data = ''
        self.error = ''
        self.timeout = reactor.callLater(cmd.defaultTimeout, self.timedOut)

    def timedOut(self):
        self.server.log.error("Command %s timed out" % self.cmd.id)
        self.timeout = None

    def processEnded(self, reason):
        self.server.log.info("Command finished: %s" % reason)
        if self.data:
            self.server.log.debug("Command %s says: %s", self.cmd.id, self.data)
        if self.error:
            self.server.log.error("Command %s error: %s", self.cmd.id, self.error)
        if self.timeout:
            reactor.cancelCallLater(self.timeout)
            self.timeout = None

    def outReceived(self, text):
        self.data += text

    def errReceived(self, text):
        self.error += text
        

class ZenActions(ZCmdBase):
    """
    Take actions based on events in the event manager.
    Start off by sending emails and pages.
    """

    lastCommand = None

    addstate = "INSERT INTO alert_state VALUES ('%s', '%s', '%s')"

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
              "  WHERE userid='%s' AND rule='%s')")
            
    clearsel = ("SELECT %s, h.evid FROM history h, alert_state a "
                " WHERE h.evid=a.evid AND a.userid='%s' AND a.rule='%s'")

    clearEventSelect = ("SELECT %s "
                        "  FROM history clear, history event "
                        " WHERE clear.evid = event.clearid "
                        "   AND event.evid = '%s'")


    def __init__(self):
        ZCmdBase.__init__(self)
        self.schedule = Schedule(self.options, self.dmd)
        self.actions = []
        self.loadActionRules()
        if not self.options.fromaddr:
            self.options.fromaddr = "zenoss@%s" % socket.getfqdn()
        self.updateCheck = UpdateCheck()
        self.sendEvent(Event.Event(device=socket.getfqdn(), 
                        eventClass=AppStart, 
                        summary="zenactions started",
                        severity=0, component="zenactions"))

    def loadActionRules(self):
        """Load the ActionRules into the system.
        """
        self.actions = []
        for us in self.dmd.ZenUsers.getAllUserSettings():
            userid = us.getId()
            self.log.debug("loading action rules for:%s", userid)
            for ar in us.objectValues(spec="ActionRule"):
                if not ar.enabled: continue
                self.actions.append(ar)
                self.log.debug("action:%s for:%s loaded", ar.getId(), userid)


    def execute(self, db, stmt):
        self.lastCommand = stmt
        self.log.debug(stmt)
        return db.cursor().execute(stmt)


    def query(self, db, stmt):
        self.lastCommand = stmt
        self.log.debug(stmt)
        curs = db.cursor()
        curs.execute(stmt)
        return curs.fetchall()


    def getUrl(self, evid):
        return '%s/zport/dmd/ZenEventManager/eventFields?evid=%s' % (
            self.options.zopeurl, evid)

            
    def getEventsUrl(self, device):
        return '%s%s/viewEvents' % (
                    self.options.zopeurl, device.getPrimaryUrlPath())


    def getAckUrl(self, evid):
        return '%s/zport/dmd/Events/manage_ackEvents?evids=%s&zenScreenName=viewEvents' % (self.options.zopeurl, evid)


    def getDeleteUrl(self, evid):
        return '%s/zport/dmd/Events/manage_deleteEvents' % self.options.zopeurl + \
               '?evids=%s&zenScreenName=viewHistoryEvents' % evid


    def getUndeleteUrl(self, evid):
        return '%s/zport/dmd/Events/manage_undeleteEvents' % self.options.zopeurl + \
               '?evid=%s&zenScreenName=viewEvents' % evid


    def processRules(self, db, zem):
        """Run through all rules matching them against events.
        """
        for ar in self.actions:
            try:
                self.lastCommand = None
                # call sendPage or sendEmail
                actfunc = getattr(self, "send"+ar.action.title())
                self.processEvent(db, zem, ar, actfunc)
            except (SystemExit, KeyboardInterrupt, OperationalError, POSError):
                raise
            except:
                if self.lastCommand:
                    self.log.warning(self.lastCommand)
                self.log.exception("action:%s",ar.getId())

    def checkVersion(self, db, zem):
        self.updateCheck.check(db, zem)
        import transaction
        transaction.commit()

    def processEvent(self, db, zem, context, action):
        fields = context.getEventFields()
        userid = context.getUserid()
        # get new events
        nwhere = context.where.strip() or '1 = 1'
        if context.delay > 0:
            nwhere += " and firstTime + %s < UNIX_TIMESTAMP()" % context.delay
        q = self.newsel % (",".join(fields), nwhere, userid, context.getId())
        for result in self.query(db, q):
            evid = result[-1]
            data = dict(zip(fields, map(zem.convert, fields, result[:-1])))
            data['eventUrl'] = self.getUrl(evid)
            device = self.dmd.Devices.findDevice(data.get('device', None))
            if device:
                data['eventsUrl'] = self.getEventsUrl(device)
            else:
                data['eventsUrl'] = 'n/a'
            data['ackUrl'] = self.getAckUrl(evid)
            data['deleteUrl'] = self.getDeleteUrl(evid)
            severity = data.get('severity', -1)
            data['severityString'] = zem.getSeverityString(severity)
            if action(context, data, False):            
                addcmd = self.addstate % (evid, userid, context.getId())
                self.execute(db, addcmd)

        # get clear events
        historyFields = [("h.%s" % f) for f in fields]
        historyFields = ','.join(historyFields)
        q = self.clearsel % (historyFields, userid, context.getId())
        for result in self.query(db, q):
            evid = result[-1]
            data = dict(zip(fields, map(zem.convert, fields, result[:-1])))
            
            # get clear columns
            cfields = [('clear.%s' % x) for x in fields]
            q = self.clearEventSelect % (",".join(cfields), evid)
            
            # convert clear columns to clear names
            cfields = [('clear%s' % _capitalize(x)) for x in fields]

            # there might not be a clear event, so set empty defaults
            data.update({}.fromkeys(cfields, ""))

            # pull in the clear event data
            for values in self.query(db, q):
                values = map(zem.convert, fields, values)
                data.update(dict(zip(cfields, values)))

            data['clearOrEventSummary'] = (
                data['clearSummary'] or data['summary'])
                
            # add in the link to the url
            data['eventUrl'] = self.getUrl(evid)
            severity = data.get('severity', -1)
            data['severityString'] = zem.getSeverityString(severity)
            action(context, data, True)
            delcmd = self.clearstate % (evid, userid, context.getId())
            self.execute(db, delcmd)

    def maintenance(self, db, zem):
        """Run stored procedures that maintain the events database.
        """
        sql = 'call age_events(%s, %s);' % (
                zem.eventAgingHours, zem.eventAgingSeverity)
        try:
            self.execute(db, sql)
        except ProgrammingError:
            self.log.exception("problem with proc: '%s'" % sql)


    def heartbeatEvents(self, db):
        """Create events for failed heartbeats.
        """
        # build cache of existing heartbeat issues
        q = ("SELECT device, component "
             "FROM status WHERE eventClass = '%s'" % HeartbeatStatus)
        heartbeatState = Set(self.query(db, q))
           
        # find current heartbeat failures
        sel = "SELECT device, component FROM heartbeat "
        sel += "WHERE DATE_ADD(lastTime, INTERVAL timeout SECOND) <= NOW();"
        for device, comp in self.query(db, sel):
            self.sendEvent(
                Event.Event(device=device, component=comp,
                            eventClass=HeartbeatStatus, 
                            summary="%s %s heartbeat failure" % (device, comp),
                            severity=Event.Error))
            heartbeatState.discard((device, comp))

        # clear heartbeats
        for device, comp in heartbeatState:
            self.sendEvent(
                Event.Event(device=device, component=comp, 
                            eventClass=HeartbeatStatus, 
                            summary="%s %s heartbeat clear" % (device, comp),
                            severity=Event.Clear))

    def runEventCommand(self, cmd, data, clear = None):
        try:
            data['clear'] = (clear and '1') or '0'
            device = self.dmd.Devices.findDevice(data.get('device', ''))
            component = None
            if device:
                componentName = data.get('component')
                for c in device.getMonitoredComponents():
                    if c.id == componentName:
                        component = c
                        break
            compiled = talesCompile('string:' + cmd.command)
            environ = {'dev':device, 'component':component, 'evt':data }
            res = compiled(getEngine().getContext(environ))
            if isinstance(res, Exception):
                raise res
            prot = EventCommandProtocol(cmd, self)
            reactor.spawnProcess(prot, '/bin/sh', ('/bin/sh', '-c', res))
        except Exception:
            self.log.exception('Error running command %s', cmd.id)
        return True
        

    def eventCommands(self, db, zem):
        now = time.time()
        count = 0
        for command in zem.commands():
            if command.enabled:
                count += 1
                self.processEvent(db, zem, command, self.runEventCommand)
        self.log.info("Processed %d commands in %f", count, time.time() - now)
            

    def mainbody(self):
        """main loop to run actions.
        """
        self.loadActionRules()
        zem = self.dmd.ZenEventManager
        db = zem.connect()
        self.eventCommands(db, zem)
        self.processRules(db, zem)
        self.checkVersion(self.dmd, zem)
        self.maintenance(db, zem)
        self.heartbeatEvents(db)
        db.close()


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
        reactor.callLater(self.options.cycletime, self.runCycle)
        
    
    def run(self):
        if not self.options.cycle:
            self.schedule.run()
            return self.mainbody()
        self.schedule.start()
        self.runCycle()
        reactor.run()


    def sendEvent(self, evt):
        """Send event to the system.
        """
        self.dmd.ZenEventManager.sendEvent(evt)


    def sendHeartbeat(self):
        """Send a heartbeat event for this monitor.
        """
        timeout = self.options.cycletime*3
        evt = Event.EventHeartbeat(socket.getfqdn(), "zenactions", timeout)
        self.sendEvent(evt)


    def stop(self):
        self.running = False
        self.log.info("stopping")
        self.sendEvent(Event.Event(device=socket.getfqdn(), 
                        eventClass=AppStop, 
                        summary="zenactions stopped",
                        severity=3, component="zenactions"))

    def format(self, action, data, clear):
        fmt = action.format
        body = action.body
        if clear:
            fmt = action.clearFormat
            body = action.clearBody
        return fmt % data, body % data

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
        fmt, body = self.format(action, data, clear)
        msg = fmt % data
        recipient = action.getAddress()
        
        result, errorMsg = Utils.sendPage(recipient, msg,
                                    self.dmd.snppHost,self.dmd.snppPort)
        if result:
            self.log.info('sent page to %s: %s', recipient, msg)
        else:
            self.log.info('failed to send page to %s: %s %s', recipient, msg,
                                                                errorMsg)
        return result
        
        

    def sendEmail(self, action, data, clear = None):
        """Send an event to an email address.
        Return True if we think the email was sent, False otherwise.
        """
        import smtplib
        from email.MIMEText import MIMEText
        from email.MIMEMultipart import MIMEMultipart
        addr = action.getAddress()
        fmt, htmlbody = self.format(action, data, clear)
        htmlbody = htmlbody.replace('\n','<br/>\n')
        body = self.stripTags(htmlbody)
        emsg = MIMEMultipart('related')
        emsgAlternative = MIMEMultipart('alternative')
        emsg.attach( emsgAlternative )
        plaintext = MIMEText(body)
        html = MIMEText(htmlbody)
        html.set_type('text/html')
        emsgAlternative.attach(plaintext)
        emsgAlternative.attach(html)
        emsg['Subject'] = fmt
        emsg['From'] = self.options.fromaddr
        emsg['To'] = addr
        emsg['Date'] = DateTime().rfc822()
        result, errorMsg = Utils.sendEmail(emsg, self.dmd.smtpHost,
                    self.dmd.smtpPort, self.dmd.smtpUseTLS, self.dmd.smtpUser, 
                    self.dmd.smtpPass)
        if result:
            self.log.info("sent email:%s to:%s", fmt, addr)
        else:
            self.log.info("failed to send email to %s: %s %s", addr, fmt, 
                                                                    errorMsg)
        return result


    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--cycletime',
            dest='cycletime', default=60, type="int",
            help="check events every cycletime seconds")
        self.parser.add_option('--fromaddr',
            dest='fromaddr', default="",
            help="address from which email is sent")
        self.parser.add_option(
            '--zopeurl', dest='zopeurl',
            default='http://%s:%d' % (socket.getfqdn(), 8080),
            help="http path to the root of the zope server")


    def sigTerm(self, signum, frame):
        'controlled shutdown of main loop on interrupt'
        try:
            ZCmdBase.sigTerm(self, signum, frame)
        except SystemExit:
            reactor.stop()

if __name__ == "__main__":
    za = ZenActions()
    import logging
    logging.getLogger('zen.Events').setLevel(20)
    za.run()
