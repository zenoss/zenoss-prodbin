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
import copy
import types
import cPickle as pickle
from threading import Lock
from os import path
from datetime import datetime

from ZenEvents.Event import EventFromDict

defaultPickleName = "savedevents.pkl"

class EventUpdateError(Exception):
    """update of event failed due to outdated serial number"""
    pass
    
class EventManager(object):
   
    def __init__(self, savefile=defaultPickleName):
        self.eventlock = Lock()
        self.savefile = savefile
        self.nextoid = 0L
        self.loadevents()

    def addevent(self, event):
        if type(event) == types.DictType:
            event = EventFromDict(event)
        self.eventlock.acquire(1)
        oid = self.getnextoid()
        event._oid = oid
        self.events[oid] = event
        self.eventlock.release()
        return oid

    def updateevent(self, event):
        self.eventlock.acquire(1)
        if self.events.has_key(event._oid):
            curev = self.events[event._oid]
            if curev._serial > event._serial:
                raise EventUpdateError, \
                    "Update failed because serial %s is less than current serial %s" % (event._serial, curev._serial)
            event._serial += 1
            event.lastupdate = datetime.utcnow()
            self.events[event._oid] = event
        self.eventlock.release()
        
    def getevent(self, oid):
        self.eventlock.acquire(1)
        ev = self.events.get(oid)
        ev = copy.copy(ev)
        self.eventlock.release()
        return ev

    def getevents(self, evfilter=None):
        self.eventlock.acquire(1)
        evresults = filter(evfilter, self.events.values())
        self.eventlock.release()
        return evresults

    def getDeviceEvents(self, device):
        return self.getevents(lambda x: x.device == device)

    def getRegexEvents(self, regex):
        regex = re.compile(regex)
        return self.getevents(lambda x: regex.search(x.gettext()))

    def getnextoid(self):
        """get the next oid number"""
        oid = self.nextoid
        self.nextoid += 1
        return oid

    def loadevents(self):
        """load events from pickle file then set nextoid"""
        self.eventlock.acquire(1)
        if path.exists(self.savefile):
            self.events = pickle.load(open(self.savefile, 'r'))
            oids = self.events.keys()
            oids.sort()
            self.nextoid = oids[-1] + 1
        else:
            self.events = {}
            self.nextoid = 0
        self.eventlock.release()
        
    def saveevents(self):
        """save events to pickle file"""
        self.eventlock.acquire(1)
        pickle.dump(self.events, open(self.savefile, 'w'),2)
        self.eventlock.release()
