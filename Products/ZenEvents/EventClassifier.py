###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__="""

Event classifier classifies events based on their summary text.  It 
uses a positional index to determin the class.  So for each word in the
summary it looks for the same word or wild card to determine which classes
that word in that position could be part.

positionIndex is an array of dictionaries.  Each positoin of the array
represents the position of the word in the summary string.  The value
is a dictionary with the words as keys and a tuple of classids as values.
"""

import copy
from os import path
from sets import Set
from threading import Lock
import logging

from Products.ZenUtils.Exceptions import ZentinelException

class EventClassNotFound(ZentinelException): pass

class EventClassNotUnique(ZentinelException): pass

class EventClassifier(object):

    def __init__(self, templatesource):
        self.positionIndex = []
        self.templatesource = templatesource
        self.indexlock = Lock()
        #log = logging.getLogger("EventClassifier")
        #log.setLevel(logging.DEBUG)

    
    def classify(self, event):
        words = event.summary.split()
        if hasattr(event, "process"):
            words.insert(0,event.process)
        if len(words) > len(self.positionIndex):
            raise EventClassNotFound, "event summary longer than position index"
        classids = None 
        classid = -1
        for i in range(len(words)):
            word = words[i]
            index = self.positionIndex[i]
            if index.has_key('*'):
                if not classids:
                    classids = copy.copy(index['*'])
                else:
                    classids = classids.union(index['*'])
            if index.has_key(word):
                if not classids: 
                    classids = copy.copy(index[word])
                else:
                    classids = classids.intersection(index[word])
            if len(classids) == 1:
                classid = classids.pop()
                break
            elif len(classids) == 0:
                raise EventClassNotFound, \
                    "no class found for words: " + " ".join(words)
        if classid == -1:
            raise EventClassNotUnique, \
                "could not find unique classid possabilites are: ", classids
        #logging.debug("found classid %s for words: %s" % 
        #                (classid, " ".join(words)))
        return classid 
                 

    def learn(self):
        """build event classes based on log data"""
        pass


    def buildIndex(self):
        """get a list of summary templates 
        and build our positionIndex from it"""
        self.indexlock.acquire()
        templates = self.readTemplates()
        for process, summary, classid in templates:
            words = summary.split()
            if process: words.insert(0, process)
            lendiff = len(words) - len(self.positionIndex)
            if lendiff > 0: 
                for i in range(lendiff): 
                    self.positionIndex.append({})
            for i in range(len(words)):
                word = words[i]
                if not self.positionIndex[i].has_key(word):
                    self.positionIndex[i][word] = Set()
                self.positionIndex[i][word].add(classid)
        # need to do a second pass to clear out unneeded positions 
        # and to determin if a class can't be identified uniquely
        self.indexlock.release()


    def readTemplates(self):
        templates = []
        if "http" in self.templatesource:
            # load over xmlrpc
            pass
        elif path.exists(self.templatesource):
            file = open(self.templatesource, "r")
            for line in file.readlines():
                if line.find("#") == 0: continue
                process, summary, classid = line.split('||')
                templates.append((process,summary,int(classid)))
            file.close()
        return templates 
