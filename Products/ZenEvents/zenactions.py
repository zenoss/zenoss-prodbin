import os
import re
import socket
import time
import Globals

from Products.ZenUtils.ZCmdBase import ZCmdBase

class ZenActions(ZCmdBase):
    """
    Take actions based on events in the event manager.
    Start off by sending emails and pages.
    """


    addstate = "insert into alert_state values ('%s', '%s')"
    clearstate = "delete from alert_state where evid='%s' and userid='%s'"


    def __init__(self):
        ZCmdBase.__init__(self)
        self.loadActionRules()
        if not self.options.fromaddr:
            self.options.fromaddr = "zenmon@%s" % socket.getfqdn()
        

    def loadActionRules(self):
        """Load the ActionRules into the system.
        """
        self.actions = []
        for us in self.dmd.ZenUsers.getAllUserSettings():
            userid = us.getId()
            self.log.debug("loading aciton rules for:%s", userid)
            for ar in us.objectValues(spec="ActionRule"):
                if not ar.enabled: continue
                if ar.action == "page": addr = us.pager
                elif ar.action == "email": addr = us.email
                self.actions.append((userid, ar.where, ar.format,
                                     ar.action, addr, ar.delay))
                self.log.debug("aciton:%s for:%s loaded", ar.getId(), userid)
                

    def processRules(self):
        """Run through all rules matching them against events.
        """
        zem = self.dmd.ZenEventManager
        db = zem.connect()
        curs = db.cursor()
        for userid, where, format, action, addr, delay in self.actions:
            fields = re.findall("%\((\S+)\)s", format)
            data = {}
            data = data.fromkeys(fields,"")
            # get new events
            nwhere = where
            if delay > 0:
                nwhere =  nwhere+""" and firstTime + %s < UNIX_TIMESTAMP()"""%(
                            delay)
            newsel = """select %s, evid from status where %s and evid not in 
                        (select evid from alert_state where userid='%s')""" % (
                        ",".join(fields), nwhere, userid)
            self.log.debug(newsel)
            curs.execute(newsel)
            for result in curs.fetchall():
                evid = result[-1]
                result = map(zem.convert, fields, result[:-1])
                for k, v in zip(fields, result): data[k]=v
                msg = format % data
                actfunc = getattr(self, "send"+action.title())
                actfunc(msg, addr)
                addcmd = self.addstate%(evid, userid)
                self.log.debug(addcmd)
                curs.execute(addcmd)
                 
            # get clear events
            clearsel = """select %s, evid from history where %s and evid in 
                        (select evid from alert_state where userid='%s')""" % (
                        ",".join(fields), where, userid)
            self.log.debug(clearsel)
            curs.execute(clearsel)
            format = "CLEAR: " + format
            for result in curs.fetchall():
                evid = result[-1]
                result = map(zem.convert, fields, result[:-1])
                for k, v in zip(fields, result): data[k]=v
                msg = format % data
                actfunc = getattr(self, "send"+action.title())
                actfunc(msg, addr)
                delcmd = self.clearstate%(evid, userid)
                self.log.debug(delcmd)
                curs.execute(delcmd)
        db.close()


    def run(self):
        if not self.options.cycle: return self.processRules()
        while 1:
            try:
                start = time.time()
                self.loadActionRules()
                self.processRules()
                self.log.info("processed %s rules in %.2f secs", 
                               len(self.actions), time.time()-start)
            except (SystemExit, KeyboardInterrupt): raise
            except:
                self.log.exception("unexpected exception")
            time.sleep(self.options.cycletime)


    def stop(self):
        self.running = False
        self.log.info("stopping")


    def sendPage(self, msg, addr):
        """Send and event to a pager.
        """
        import Pager
        rcpt = Pager.Recipient(addr)
        msg = Pager.Message(msg)
        #msg.callerid = "zenmon"
        page = Pager.Pager((rcpt,), msg, self.options.snpphost, 
                                         self.options.snppport)
        page.send()
        self.log.info("sent page:%s to:%s", msg, addr)
        

    def sendEmail(self, msg, addr):
        """Send an event to an email address.
        """
        import smtplib
        from email.MIMEText import MIMEText
        emsg = MIMEText(msg)
        emsg['Subject'] = "ZenMon: "
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
