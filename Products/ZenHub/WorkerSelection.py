###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from collections import defaultdict
from itertools import ifilter
from zope.component import queryUtility, getUtilitiesFor
from zope.interface import implements
from .interfaces import IWorkerSelectionAlgorithm

class InOrderSelection(object):
    """
    Simple selection algorithm that returns workers in the
    order in which they are given.
    """
    implements(IWorkerSelectionAlgorithm)

    def getCandidateWorkerIds(self, workers, options):
        return (i for i, worker in enumerate(workers) if not worker.busy)

class ReservationAwareSelection(InOrderSelection):
    """
    Selection algorithm that returns workers in the
    order in which they are given, and only returns workers
    above the reserved threshold.
    """
    implements(IWorkerSelectionAlgorithm)

    def getCandidateWorkerIds(self, workers, options):
        return ifilter(lambda i: i >= options.workersReservedForEvents,
                       super(ReservationAwareSelection, self)\
                       .getCandidateWorkerIds(workers, options))

class ReversedReservationAwareSelection(ReservationAwareSelection):
    """
    Selection algorithm that returns workers in the reverse
    order in which they are given, and only returns workers
    above the reserved threshold.
    """
    implements(IWorkerSelectionAlgorithm)

    def getCandidateWorkerIds(self, workers, options):
        selection = super(ReversedReservationAwareSelection, self)\
                            .getCandidateWorkerIds(workers, options)
        return reversed(list(selection))


class WorkerSelector(object):
    """
    Singleton worker selector that apportions work to zenhub workers based on the
    configured utilities per method name.
    """

    def __init__(self, options):
        self.options = options
        self.selectors = {}

        for name, utility in getUtilitiesFor(IWorkerSelectionAlgorithm):
            self.selectors[name] = utility
        self.defaultSelector = self.selectors['']

    def getCandidateWorkerIds(self, methodName, workerlist):
        selector = self.selectors.get(methodName, self.defaultSelector)
        return selector.getCandidateWorkerIds(workerlist, self.options)
