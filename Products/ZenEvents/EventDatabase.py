###############################################################################
#
#   Copyright (c) 2004 Zentinel Systems. 
#
#   This library is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public
#   License as published by the Free Software Foundation; either
#   version 2.1 of the License, or (at your option) any later version.
#
###############################################################################

import re
import os
import copy
import types
import gc
import cPickle as pickle
from threading import RLock, Timer
from os import path
from datetime import datetime

from Products.ZenEvents.Event import EventFromDict

defaultPickleName = "savedevents"
defaultSaveTime = 3600.0 

class EventUpdateError(Exception):
    """update of event failed due to outdated serial number"""
    pass
    
class EventDatabase(object):
   
    def __init__(self, savefile=defaultPickleName, 
                        savetime=defaultSaveTime,
                        journal=True):

        self.journal = journal
        self.savefile = savefile + ".pkl"
        self.journalfile = savefile + ".jnl"
        self.savetime = savetime
        self.nextoid = 0L
        self.eventlock = RLock()
        if self.savetime > 0:
            self.setimer = Timer(self.savetime, self.saveevents)
            self.setimer.setDaemon(True)
            self.setimer.start()
        self.loadevents()

    def __del__(self):
        if self.savetime > 0:
            self.setimer.cancel()

    def addevent(self, event, recover=False):
        """add or update an event in the database"""
        oid = None
        if type(event) == types.DictType:
            event = EventFromDict(event)
        if event._oid != None:
            self.updateevent(event)
            oid = event._oid
        else:
            self.eventlock.acquire()
            oid = self.getnextoid()
            event._oid = oid
            self.events[oid] = event
            self.eventlock.release()
        if not recover and self.journal:
            self.journalevent(event)            
        return oid

    def journalevent(self, event):
        """send pickle of event to journal file"""
        jf = open(self.journalfile, "a")
        pickle.dump(event, jf, 2)
        jf.close()

    def updateevent(self, event):
        self.eventlock.acquire()
        if self.events.has_key(event._oid):
            curev = self.events[event._oid]
            if curev._serial > event._serial:
                raise EventUpdateError, \
                    "Update failed because serial %s is less than current serial %s" % (event._serial, curev._serial)
            event._serial += 1
            event.lastupdate = datetime.utcnow()
        self.events[event._oid] = event
        self.eventlock.release()
    
    def deleteevents(self, evfilter=None):
        self.eventlock.acquire()
        if not evfilter: self.events.clear() 
        for ev in self.getevents(evfilter):
            del self.events[ev._oid]
        self.eventlock.release()

    def deleteevent(self, oid):
        self.eventlock.acquire()
        del self.events[oid]
        self.eventlock.release()

    def getevent(self, oid):
        self.eventlock.acquire()
        ev = self.events.get(oid)
        ev = copy.copy(ev)
        self.eventlock.release()
        return ev

    def getevents(self, evfilter=None):
        self.eventlock.acquire()
        evresults = filter(evfilter, self.events.values())
        self.eventlock.release()
        return evresults

    def countevents(self, evfilter=None):
        return len(self.getevents(evfilter))
    
    def getDeviceEvents(self, device):
        """query for events for a specific device name must be FQDN"""
        return self.getevents(lambda x: x.device == device)

    def getRegexEvents(self, regex):
        """query for events by regex will combine all text in event for match"""
        regex = re.compile(regex)
        return self.getevents(lambda x: regex.search(x.gettext()))

    def getEvents(self, lambdastr=None):
        """query for events with a lambda function string"""
        if not lambdastr: return self.getevents()
        if not lambdastr.startswith("lambda"):
            lambdastr = "lambda ev: " + lambdastr
        evfilter = eval(lambdastr)
        return self.getevents(evfilter)
            
    def loadevents(self):
        """load events from pickle file then set nextoid"""
        self.eventlock.acquire()
        if path.exists(self.savefile):
            self.events = pickle.load(open(self.savefile, 'r'))
        else:
            self.events = {}
            self.nextoid = 0
        if path.exists(self.journalfile):
            jf = open(self.journalfile, "r")
            i = 0
            while 1:
                i += 1
                try:
                    ev = pickle.load(jf)
                    self.addevent(ev,recover=True)
                except EOFError: break
                except pickle.UnpicklingError:
                    print "failed loading pickle number %d" % i
                    break
            jf.close()
        self.setnextoid()      
        self.eventlock.release()
        self.saveevents()

    def saveevents(self):
        """save events to pickle file"""
        if self.savetime > 0:
            self.setimer.cancel()
        self.eventlock.acquire()
        pickle.dump(self.events, open(self.savefile, 'w'),2)
        if path.exists(self.journalfile):
            os.remove(self.journalfile)
        self.eventlock.release()
        if self.savetime > 0:
            self.setimer = Timer(self.savetime, self.saveevents)
            self.setimer.setDaemon(True)
            self.setimer.start()
        gc.collect()
    
  
    def close(self):
        self.eventlock.acquire()
        self.setimer.cancel()
        self.saveevents()
        self.eventlock.release()


    def getnextoid(self):
        """get the next oid number"""
        oid = self.nextoid
        self.nextoid += 1
        return oid

    def setnextoid(self):
        maxoid = 0L
        if len(self.events) > 0:
            maxoid = max(self.events.keys())
        self.nextoid = maxoid + 1


