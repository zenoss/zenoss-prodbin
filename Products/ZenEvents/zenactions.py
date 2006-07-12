import os
import socket
import time
from sets import Set
import Globals

from ZODB.POSException import POSError
from _mysql_exceptions import OperationalError, ProgrammingError 

from Products.ZenUtils.ZCmdBase import ZCmdBase
from ZenEventClasses import AppStart, AppStop, HeartbeatStatus
import Event

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

    newsel = ("SELECT %s, evid FROM status WHERE %s AND evid NOT IN " 
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
        self.actions = []
        self.loadActionRules()
        if not self.options.fromaddr:
            self.options.fromaddr = "zenoss@%s" % socket.getfqdn()
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


    def processRules(self, db, zem):
        """Run through all rules matching them against events.
        """
        for ar in self.actions:
            try:
                self.lastCommand = None
                self.processActionRule(db, zem, ar)
            except (SystemExit, KeyboardInterrupt, OperationalError, POSError):
                raise
            except:
                if self.lastCommand:
                    self.log.warning(self.lastCommand)
                self.log.exception("action:%s",ar.getId())


    def processActionRule(self, db, zem, ar):
        fields = ar.getEventFields()
        userid = ar.getUserid()
        addr = ar.getAddress()
        actfunc = getattr(self, "send"+ar.action.title())
        # get new events
        nwhere = ar.where
        if ar.delay > 0:
            nwhere += " and firstTime + %s < UNIX_TIMESTAMP()" % ar.delay
        q = self.newsel % (",".join(fields), nwhere, userid, ar.getId())
        for result in self.query(db, q):
            evid = result[-1]
            data = dict(zip(fields, map(zem.convert, fields, result[:-1])))
            actfunc = getattr(self, "send"+ar.action.title())
            actfunc(ar.format % data, addr)
            addcmd = self.addstate % (evid, userid, ar.getId())
            self.execute(db, addcmd)

        # get clear events
        q = self.clearsel % (",".join(fields),userid,ar.getId())
        for result in self.query(db, q):
            evid = result[-1]
            data = dict(zip(fields, map(zem.convert, fields, result[:-1])))
            cldata = {}
            cfields = map(lambda x: 'clear.%s' % x, fields)
            q = self.clearEventSelect % (",".join(cfields), evid)
            for values in self.query(db, q):
                cldata.update(dict(zip(fields, values)))
            # FIXME: provide cleared data in cldata
            data.update(cldata)
            actfunc(ar.format % data, addr)
            delcmd = self.clearstate % (evid, userid, ar.getId())
            self.execute(db, delcmd)


    def maintenance(self, db, zem):
        """Run stored procedures that maintain the events database.
        """
        for proc in zem.maintenanceProcedures:
            try:
                self.execute(db, "call %s();" % proc)
            except ProgrammingError:
                self.log.exception("problem with proc: '%s'", proc)


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
            

    def mainbody(self):
        """main loop to run actions.
        """
        self.loadActionRules()
        zem = self.dmd.ZenEventManager
        db = zem.connect()
        self.processRules(db, zem)
        self.maintenance(db, zem)
        self.heartbeatEvents(db)
        db.close()
        
    
    def run(self):
        if not self.options.cycle: 
            return self.mainbody()
        while 1:
            try:
                start = time.time()
                self.syncdb()
                self.mainbody()
                self.log.info("processed %s rules in %.2f secs", 
                               len(self.actions), time.time()-start)
                self.sendHeartbeat()
            except (SystemExit, KeyboardInterrupt): raise
            except:
                self.log.exception("unexpected exception")
            time.sleep(self.options.cycletime)


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


    def sendPage(self, msg, addr):
        """Send and event to a pager.
        """
        import Pager
        rcpt = Pager.Recipient(addr)
        pmsg = Pager.Message(msg)
        #pmsg.callerid = "zenoss"
        page = Pager.Pager((rcpt,), pmsg, self.options.snpphost, 
                                         self.options.snppport)
        page.send()
        self.log.info("sent page:%s to:%s", msg, addr)
        

    def sendEmail(self, msg, addr):
        """Send an event to an email address.
        """
        import smtplib
        from email.MIMEText import MIMEText
        emsg = MIMEText(msg)
        emsg['Subject'] = "[zenoss] %s" % msg[:128]
        emsg['From'] = self.options.fromaddr
        emsg['To'] = addr
        server = smtplib.SMTP(self.options.smtphost, self.options.smtpport)
        server.sendmail(self.options.fromaddr, (addr,), emsg.as_string())
        server.quit()
        self.log.info("sent email:%s to:%s", msg, addr)


    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--cycletime',
            dest='cycletime', default=60, type="int",
            help="check events every cycletime seconds")
        self.parser.add_option('--fromaddr',
            dest='fromaddr', default="",
            help="address from which email is sent")
        self.parser.add_option('--snpphost',
            dest='snpphost', default="localhost",
            help="snpp server to used when sending pages")
        self.parser.add_option('--snppport',
            dest='snppport', default=444, type="int",
            help="snpp port used when sending pages")
        self.parser.add_option('--smtphost',
            dest='smtphost', default="localhost",
            help="smtp server to used when sending pages")
        self.parser.add_option('--smtpport',
            dest='smtpport', default=25, type="int",
            help="smtp port used when sending pages")

if __name__ == "__main__":
    za = ZenActions()
    import logging
    logging.getLogger('zen.Events').setLevel(20)
    za.run()
