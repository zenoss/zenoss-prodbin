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
import cPickle as pickle
from threading import Lock
from os import path

defaultPickleName = "savedevents.pkl"

class EventManager(object):
   
    def __init__(self, savefile=defaultPickleName):
        self.eventlock = Lock()
        self.savefile = savefile
        self.nextoid = 0L
        self.loadevents()

    def addevent(self, event):
        self.eventlock.acquire(1)
        oid = self.getoid()
        event.oid = oid
        self.events[oid] = event
        self.eventlock.release()

    def getevents(self, evfilter=None):
        self.eventlock.acquire(1)
        evresults = filter(evfilter, self.events.values())
        self.eventlock.release()
        return evresults

    def getDeviceEvents(self, device):
        return self.getevents(lambda x: x.device == device)

    def getRegexEvents(self, regex):
        regex = re.compile(regex)
        return self.getevents(lambda x: regex.search(x.getText()))

    def getevent(self, oid):
        self.eventlock.acquire(1)
        ev =  self.events.get(oid)
        self.eventlock.release()
        return ev

    def getoid(self):
        oid = self.nextoid
        self.nextoid += 1
        return oid

    def loadevents(self):
        self.eventlock.acquire(1)
        if path.exists(self.savefile):
            self.events = pickle.load(open(self.savefile, 'r'))
        else:
            self.events = {}
        self.eventlock.release()
        
    def saveevents(self):
        self.eventlock.acquire(1)
        pickle.dump(self.events, open(self.savefile, 'w'),2)
        self.eventlock.release()
        
