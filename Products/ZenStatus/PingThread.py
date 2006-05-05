import threading
import Queue
import logging
log = logging.getLogger("PingThread")

from Ping import Ping, PingJob

class PingThread(threading.Thread, Ping):
    """
    PingThread takes pingjobs off a Queue and pings them.
    """
    
    def __init__(self, reportqueue,tries=2, timeout=2, chunkSize=10):
        threading.Thread.__init__(self)
        Ping.__init__(self, tries, timeout, chunkSize)
        self.setDaemon(1)
        self.setName("PingThread")
        self.sendqueue = Queue.Queue()
        self.reportqueue = reportqueue


    def sendPackets(self):
        """Send any packets that are in our queue up to numbtosend.
        """
        try:
            numbtosend = self.chunkSize - len(self.jobqueue)
            for i in range(numbtosend):
                pingJob = self.sendqueue.get(False)
                self.devcount += 1
                self.sendPacket(pingJob)
        except Queue.Empty: pass 


    def sendPing(self, pj):
        """Called from main thread to add new pingjob to send queue.
        """
        self.incount += 1
        self.sendqueue.put(pj)
        


    def reportPingJob(self, pj):
        """Pass pingJobs back to our master thread when done.
        """
        self.outcount += 1
        self.reportqueue.put(pj)


    def run(self):
        """Start this thread. Exit by setting self.morepkts.
        """
        log.info("starting")
        self.eventLoop(self.sendqueue)
        log.info("stopped")


    def stop(self):
        log.info("stopping...")
        self.morepkts = False
        self.join(5)
    

if __name__ == "__main__":
    import sys
    import Queue
    logging.basicConfig()
    log = logging.getLogger()
    log.setLevel(10)
    sendqueue = Queue.Queue()
    reportqueue = Queue.Queue()
    pt = PingThread(sendqueue, reportqueue)
    if len(sys.argv) > 1: targets = sys.argv[1:]
    else: targets = ("127.0.0.1",)
    for ip in targets:
        pj = PingJob(ip)
        sendqueue.put(pj)
    pt.start()
    sent = len(targets)
    received = 0
    while received < sent:
        try:
            pj = reportqueue.get(False)
            received += 1
        except Queue.Empty: pass
    pt.morepkts = False
    pt.join(2)
