##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import enum

from collections import Iterator
from itertools import cycle, chain, count
from metrology import Metrology
from metrology.registry import registry
from metrology.instruments import Gauge


class OrderedEnum(enum.Enum):
    """ Enum classes that inherit OrderedEnum will allow that Enum's
    values to participate in inequality relationships.  I.e. the >, >=, <,
    and <= operators will work on that Enum's values.
    """

    # OrderedEnum is copied from the standard Python enum documentation.

    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented


@enum.unique
class ZenHubPriority(OrderedEnum):
    """Specifies different priority values that requests to ZenHub
    can be associated with.

    Priority order is ascending; lowest value has highest priority.
    """
    EVENTS = 1
    SINGLE_MODELING = 2
    OTHER = 3
    MODELING = 4


def _build_weighted_list(data):
    """Given a set of sortable elements, return an immutable sequence that
    reflects each element's sort position by some weight evenly distributed
    throughout the returned sequence.

    >>> data = ['a', 'b', 'c']
    >>> _build_weighted_list(data)
    ('a', 'a', 'b', 'a', 'a', 'b', 'c', 'a', 'a', 'b', 'a')

    The element that sorts to the first position has highest weight, so
    'a' will have the highest weight.  Each subsequence element will have
    less weight.  The element that sorts to the end has the lowest weight.

    The weight algorithm is 2^(len(p) - n) - 1, where len(p) is the number
    of elements and n is the element's position in the sorted sequence.
    """
    # Sort the data
    elements = tuple(sorted(data))

    # Generate a series of weights.  The first element should have the
    # highest weight.
    weights = [(2 ** n) - 1 for n in range(len(elements), 0, -1)]

    # Build a list of element lists where each element list has a length
    # matching their weight. E.g. given elements ('a', 'b') and weights
    # [3, 1], the result is [['a', 'a', 'a'], ['b']].
    weighted_series = (
        [element] * weight
        for element, weight in zip(elements, weights)
    )

    # Give each series element an index between 0 and 1. E.g. given
    #    [['a', 'a', 'a'],
    #     ['b']]
    # then the 'indexed' sequence would be
    #    [[(0.25, 'a'), (0.5, 'a'), (0.75, 'a')],
    #     [(0.5, 'b')]]
    indexed = (
        zip(
            count(
                start=1.0 / (len(series) + 1),
                step=1.0 / (len(series) + 1)
            ),
            series
        )
        for series in weighted_series
    )

    # Flatten the indexed series, e.g. converts
    #    [[(0.25, 'a'), (0.5, 'a'), (0.75, 'a')], [(0.5, 'b')]]
    # to
    #    [(0.25, 'a'), (0.5, 'a'), (0.75, 'a'), (0.5, 'b')]
    flattened = chain.from_iterable(indexed)

    # Sort the indexed element values, e.g. converts
    #    [(0.25, 'a'), (0.5, 'a'), (0.75, 'a'), (0.5, 'b')]
    # to
    #    [(0.25, 'a'), (0.5, 'a'), (0.5, 'b'), (0.75, 'a')]
    sorted_by_index = sorted(flattened)

    # Return the indexed sorted elements minus the index values,
    # e.g. converts
    #    [(0.25, 'a'), (0.5, 'a'), (0.5, 'b'), (0.75, 'a')]
    # to
    #    ('a', 'a', 'b', 'a')
    # and returns it as a tuple.
    return tuple(v for _, v in sorted_by_index)


class _MessagePriorityMap(dict):
    """Extends dict to provide ZenHubPriority.OTHER as the default
    return value if the requested key is not found.
    """

    def get(self, message, default=ZenHubPriority.OTHER):
        return super(_MessagePriorityMap, self).get(message, default)


# Maps request messages to ZenHubPriority values.  _MessagePriorityMap is
# used since all unmapped messages should default to ZenHubPriority.OTHER.
_message_priority_map = _MessagePriorityMap({
    "sendEvent":           ZenHubPriority.EVENTS,
    "sendEvents":          ZenHubPriority.EVENTS,
    "applyDataMaps":       ZenHubPriority.MODELING,
    "singleApplyDataMaps": ZenHubPriority.SINGLE_MODELING
})


class PriorityListLengthGauge(Gauge):

    def __init__(self, worklist, priority):
        self.__worklist = worklist
        self.__priority = priority

    @property
    def value(self):
        return self.__worklist.length_of(self.__priority)


class WorklistLengthGauge(Gauge):

    def __init__(self, worklist):
        self.__worklist = worklist

    @property
    def value(self):
        return len(self.__worklist)


_gauge_priority_map = {
    "zenhub.eventWorkList": ZenHubPriority.EVENTS,
    "zenhub.admWorkList": ZenHubPriority.MODELING,
    "zenhub.otherWorkList": ZenHubPriority.OTHER,
    "zenhub.singleADMWorkList": ZenHubPriority.SINGLE_MODELING,
}


def register_metrics_on_worklist(worklist):
    metricNames = {x[0] for x in registry}

    for metricName, priority in _gauge_priority_map.iteritems():
        if metricName not in metricNames:
            gauge = PriorityListLengthGauge(worklist, priority)
            Metrology.gauge(metricName, gauge)

    if "zenhub.workList" not in metricNames:
        gauge = WorklistLengthGauge(worklist)
        Metrology.gauge("zenhub.workList", gauge)


def get_worklist_metrics(worklist):
    gauges = {
        priority: worklist.length_of(priority)
        for priority in ZenHubPriority
    }
    return gauges


class _PrioritySelection(Iterator):
    """Implements an iterator that produces priority values.

    Higher priority values are produced more frequently than lower
    priority values.
    """

    def __init__(self, priorities):
        """Initializes a _PrioritySelection object.

        @param priorities {sequence} The priorities to iterate over.
        """
        self.__priorities = priorities

        # Build a priority selection sequence for all priorities
        self.__selection = _build_weighted_list(self.__priorities)
        # Use a cycle iterator over the priority sequence
        self.__iter = cycle(self.__selection)

    @property
    def priorities(self):
        return self.__priorities

    def next(self):
        return next(self.__iter)


# List of all message priorities
_all_priorities = list(ZenHubPriority)

# List of all message priorities except MODELING
_no_adm_priorities = [ZenHubPriority.EVENTS, ZenHubPriority.OTHER]


class ZenHubWorklist(object):
    """Implements a priority queue with a fair retrieval algorithm.

    Jobs may be pushed into the queue in any order.  Each job is assigned a
    priority and stored in FIFO order by priority.

    ZenHubWorklist maintains a deterministic ordering of priorities.  When
    a job is popped, the next priority in order is selected and the first
    job with that priority is returned to the caller.  The ordering is
    designed such that higher priorities are selected more frequently than
    lower priorities.  It is never the case that all higher priority jobs
    are popped before lower priority jobs are popped.

    The ZenHubWorklist maintains two sets of priorities.  One set includes
    all job priorities and the other excludes modeling (applyDataMaps)
    related priorities.  The priority set used to select a job is
    determined by a predicate object passed into the constructor.  By
    default, jobs are selected using all job priorities.

    A job is required to have one attribute named 'method' which should
    produce a string value when read.
    """

    def __init__(self, modeling_paused=None):
        """Initializes a ZenHubWorklist object.

        If an argument is provided for the modeling_paused parameter,
        it should be function that takes no arguments and returns True
        to exclude modeling related priorities for job selection.
        """
        if modeling_paused is None:
            self.__modeling_paused = bool  # always False
        else:
            self.__modeling_paused = modeling_paused

        # Associate a list with each priority
        self.__worklists = {priority: [] for priority in ZenHubPriority}

        # All jobs priority selection
        self.__alljobs = _PrioritySelection(_all_priorities)

        # No ApplyDataMaps priority selection
        self.__noadmjobs = _PrioritySelection(_no_adm_priorities)

    def __len__(self):
        return sum(len(v) for v in self.__worklists.itervalues())

    def length_of(self, priority):
        """Returns the number of jobs currently available having the
        specified priority.
        """
        return len(self.__worklists[priority])

    def __length(self, priorities):
        return sum(len(self.__worklists[p]) for p in priorities)

    def __pop(self, selection):
        while self.__length(selection.priorities):
            priority = next(selection)
            wlist = self.__worklists[priority]
            if len(wlist):
                return wlist.pop(0)

    def pop(self):
        """Returns the next job by priority.  If no jobs are available,
        None is returned.
        """
        if self.__modeling_paused():
            return self.__pop(self.__noadmjobs)
        return self.__pop(self.__alljobs)

    def push(self, job):
        """Adds job to the worklist.

        The job's attribute, 'method', determines the priority of the job.
        """
        priority = _message_priority_map.get(job.method)
        self.__worklists.get(priority).append(job)
