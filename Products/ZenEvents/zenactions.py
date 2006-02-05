import os
import re
import socket
import time
import Globals

from ZODB.POSException import POSError
from _mysql_exceptions import OperationalError 

from Products.ZenUtils.ZCmdBase import ZCmdBase
from Event import Event
from ZenEventClasses import AppStart, AppStop


class ZenActions(ZCmdBase):
    """
    Take actions based on events in the event manager.
    Start off by sending emails and pages.
    """


    addstate = "insert into alert_state values ('%s', '%s', '%s')"

    clearstate = """delete from alert_state where evid='%s' 
                    and userid='%s' and rule='%s'"""

    newsel = """select %s, evid from status where %s and evid not in 
             (select evid from alert_state where userid='%s'and rule='%s')""" 
            
    clearsel = """select %s, evid from history where %s and evid in 
               (select evid from alert_state where userid='%s' and rule='%s')"""


    def __init__(self):
        ZCmdBase.__init__(self)
        self.loadActionRules()
        if not self.options.fromaddr:
            self.options.fromaddr = "zenoss@%s" % socket.getfqdn()
        self.sendEvent(Event(device=socket.getfqdn(), 
                        eventClass=AppStart, 
                        summary="zenactions started",
                        severity=0, component="zenoss/zenactions"))
        

    def loadActionRules(self):
        """Load the ActionRules into the system.
        """
        self.actions = []
        for us in self.dmd.ZenUsers.getAllUserSettings():
            userid = us.getId()
            self.log.debug("loading aciton rules for:%s", userid)
            for ar in us.objectValues(spec="ActionRule"):
                if not ar.enabled: continue
                self.actions.append(ar)
                self.log.debug("aciton:%s for:%s loaded", ar.getId(), userid)
                

    def processRules(self):
        """Run through all rules matching them against events.
        """
        zem = self.dmd.ZenEventManager
        db = zem.connect()
        curs = db.cursor()
        for ar in self.actions:
            cursql = ""
            try:
                fields = ar.getEventFields()
                userid = ar.getUserid()
                addr = ar.getAddress()
                data = {}
                data = data.fromkeys(fields,"")
                # get new events
                nwhere = ar.where
                if ar.delay > 0:
                    nwhere += """ and firstTime + %s < UNIX_TIMESTAMP()"""%(
                                ar.delay)
                newsel = self.newsel % (",".join(fields), nwhere,
                                        userid, ar.getId())
                self.log.debug(newsel)
                cursql = newsel
                curs.execute(newsel)
                for result in curs.fetchall():
                    evid = result[-1]
                    result = map(zem.convert, fields, result[:-1])
                    for k, v in zip(fields, result): data[k]=v
                    msg = ar.format % data
                    actfunc = getattr(self, "send"+ar.action.title())
                    actfunc(msg, addr)
                    addcmd = self.addstate%(evid, userid, ar.getId())
                    self.log.debug(addcmd)
                    cursql = addcmd
                    curs.execute(addcmd)
                     
                # get clear events
                clearsel = self.clearsel % (",".join(fields), ar.where, 
                                            userid, ar.getId())
                self.log.debug(clearsel)
                cursql = clearsel
                curs.execute(clearsel)
                format = "CLEAR: " + ar.format
                for result in curs.fetchall():
                    evid = result[-1]
                    result = map(zem.convert, fields, result[:-1])
                    for k, v in zip(fields, result): data[k]=v
                    msg = format % data
                    actfunc = getattr(self, "send"+ar.action.title())
                    actfunc(msg, addr)
                    delcmd = self.clearstate%(evid, userid, ar.getId())
                    self.log.debug(delcmd)
                    cursql = delcmd
                    curs.execute(delcmd)
            except (SystemExit, KeyboardInterrupt, OperationalError, POSError): 
                raise
            except:
                if cursql: self.log.warn(cursql)
                self.log.exception("action:%s",ar.getId())
        db.close()


    def run(self):
        if not self.options.cycle: return self.processRules()
        while 1:
            try:
                start = time.time()
                self.syncdb()
                self.loadActionRules()
                self.processRules()
                self.log.info("processed %s rules in %.2f secs", 
                               len(self.actions), time.time()-start)
            except (SystemExit, KeyboardInterrupt): raise
            except:
                self.log.exception("unexpected exception")
            time.sleep(self.options.cycletime)


    def sendEvent(self, evt):
        """Send event to the system.
        """
        self.dmd.ZenEventManager.sendEvent(evt)


    def stop(self):
        self.running = False
        self.log.info("stopping")
        self.sendEvent(Event(device=socket.getfqdn(), 
                        eventClass=AppStop, 
                        summary="zenactions stopped",
                        severity=3, component="zenoss/zenactions"))


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
    za.run()
