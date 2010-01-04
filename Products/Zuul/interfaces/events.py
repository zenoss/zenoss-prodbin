###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from zope.interface import Interface, Attribute
from Products.Zuul.interfaces import IFacade
from info import IInfo

class IEventEvent(Interface):
    """
    A Zenoss event action has occurred.
    """
    manager = Attribute("A URL to the event manager or the manager itself")
    evid = Attribute("The ID of the Zenoss event")


class IEventStateChanged(IEventEvent):
    """
    An event has changed state.
    """
    fromState = Attribute("Old state of the event")
    toState = Attribute("New state of the event")


class IEventAcknowledged(IEventStateChanged):
    """
    An event has been acknowledged.
    """


class IEventUnacknowledged(IEventStateChanged):
    """
    An event has been unacknowledged.
    """


class IEventMoved(IEventEvent):
    """
    An event has been put into a table it didn't used to be in
    """


class IEventAdded(IEventMoved):
    """
    An event has been added to the status table.
    """


class IEventReopened(IEventAdded):
    """
    An event has been moved from history to status.
    """


class IEventClosed(IEventMoved):
    """
    An event has been moved from status to history.
    """


class IEventEntity(Interface):
    """
    Marker interface for ZEvent
    """

class IEventInfo(IInfo):
    """
    Info object for events.
    """
    severity = Attribute('the event severity')
    device = Attribute('the device asscoiated with the event')
    component = Attribute('the component of device asscoiated with the event')
    eventClass = Attribute('the event class')
    summary = Attribute('a summary of the event')

class IEventFacade(IFacade):

    def fields(context=None):
        """
        Get the result fields appropriate for the context.

        @param context: An object that can have events. Defaults to dmd.Events.
        @type context: Products.ZenModel.EventView.EventView
        @return: List of strings identifying columns in SQL
        @rtype: list
        """

    def query(start, limit, sort, dir, filters=None):
        """
        Query the events database for a set of events.

        @param limit: Integer denoting the maximum number of records to
                      return
        @type limit: int
        @param start: The index of the first record to return
        @type start: int
        @param sort: The column by which to sort the results
        @type sort: str
        @param dir: Direction to sort, either ASC or DESC
        @type dir: str
        @param filters: Values for which to create filters (e.g.,
                        {'device':'^loc.*$', 'severity':[4, 5]})
        @type filters: dict or JSON str representing dict

        @return A dictionary containing the total number of matching records
                and a list of L{Products.ZenEvents.ZEvent.ZEvent} objects
        @rtype dict
        """

    def create(summary, severity, device=None, component=None, **kwargs):
        """
        Create an event.

        @param summary: The summary of the event to be created. Required.
        @type summary: str
        @param severity: Severity of the event to be created. Required.
        @type severity: int : -1 <= severity <= 5
        @param device: Name of the device with which the event should be
                       associated. Either device or component must be specified.
        @type device: str
        @param component: Name of the component with which the event should be
                          associated. Either device or component must be
                          specified.
        @type component: str

        Arbitrary keyword arguments will be added to the event as well; the
        schema may change, so these parameters will not be defined explicitly.
        @return: Dictionary containing success parameter and event ID of
                 created event, if applicable
        @rtype: dict
        """

    def acknowledge(evids=None, ranges=None, start=None, limit=None, sort=None,
               dir=None, filters=None, asof=None):
        """
        Acknowledge one or more events.

        @param evids: Event IDs of events to acknowledge. Either evids or
                      ranges must be specified; if both are specified, matching
                      event IDs in the ranges will be merged with evids.
        @type evids: list
        @param ranges: Ranges of indices of events to acknowledge. The query
                       will be executed with the other parameters specified;
                       ranges should be in terms of the results.  Either evids
                       or ranges must be specified; if both are specified,
                       matching event IDs in the ranges will be merged with
                       evids.  e.g.: [[1, 10],[15,20]]
        @type ranges: list of (start, end) pairs of indices
        @param limit: Integer denoting the maximum number of records
        @type limit: int
        @param start: The index of the first record of the query result
        @type start: int
        @param sort: The column by which to sort the records
        @type sort: str
        @param dir: Direction to sort, either ASC or DESC
        @type dir: str
        @param filters: Values for which to create filters (e.g.,
                        {'device':'^loc.*$', 'severity':[4, 5]})
        @type filters: dict or JSON str representing dict
        @param asof: Last time as of which ranges were accurate
        @type asof: float
        """

    def unacknowledge(evids=None, ranges=None, start=None, limit=None, sort=None,
               dir=None, filters=None):
        """
        Unacknowledge one or more events.

        @param evids: Event IDs of events to unacknowledge. Either evids or
                      ranges must be specified; if both are specified, matching
                      event IDs in the ranges will be merged with evids.
        @type evids: list
        @param ranges: Ranges of indices of events to unacknowledge. The query
                       will be executed with the other parameters specified;
                       ranges should be in terms of the results.  Either evids
                       or ranges must be specified; if both are specified,
                       matching event IDs in the ranges will be merged with
                       evids.  e.g.: [[1, 10],[15,20]]
        @type ranges: list of (start, end) pairs of indices
        @param limit: Integer denoting the maximum number of records
        @type limit: int
        @param start: The index of the first record of the query result
        @type start: int
        @param sort: The column by which to sort the records
        @type sort: str
        @param dir: Direction to sort, either ASC or DESC
        @type dir: str
        @param filters: Values for which to create filters (e.g.,
                        {'device':'^loc.*$', 'severity':[4, 5]})
        @type filters: dict or JSON str representing dict
        @param asof: Last time as of which ranges were accurate
        @type asof: float
        """

    def reopen(evids=None, ranges=None, start=None, limit=None, sort=None,
               dir=None, filters=None):
        """
        Reopen one or more events.

        @param evids: Event IDs of events to reopen. Either evids or ranges
                      must be specified; if both are specified, matching event
                      IDs in the ranges will be merged with evids.
        @type evids: list
        @param ranges: Ranges of indices of events to reopen. The query will be
                       executed with the other parameters specified; ranges
                       should be in terms of the results.  Either evids or
                       ranges must be specified; if both are specified,
                       matching event IDs in the ranges will be merged with
                       evids.  e.g.: [[1, 10],[15,20]]
        @type ranges: list of (start, end) pairs of indices
        @param limit: Integer denoting the maximum number of records
        @type limit: int
        @param start: The index of the first record of the query result
        @type start: int
        @param sort: The column by which to sort the records
        @type sort: str
        @param dir: Direction to sort, either ASC or DESC
        @type dir: str
        @param filters: Values for which to create filters (e.g.,
                        {'device':'^loc.*$', 'severity':[4, 5]})
        @type filters: dict or JSON str representing dict
        @param asof: Last time as of which ranges were accurate
        @type asof: float
        """

    def close(evids=None, ranges=None, start=None, limit=None, sort=None,
               dir=None, filters=None):
        """
        Close one or more events.

        @param evids: Event IDs of events to close. Either evids or ranges
                      must be specified; if both are specified, matching event
                      IDs in the ranges will be merged with evids.
        @type evids: list
        @param ranges: Ranges of indices of events to close. The query will be
                       executed with the other parameters specified; ranges
                       should be in terms of the results.  Either evids or
                       ranges must be specified; if both are specified,
                       matching event IDs in the ranges will be merged with
                       evids.  e.g.: [[1, 10],[15,20]]
        @type ranges: list of (start, end) pairs of indices
        @param limit: Integer denoting the maximum number of records
        @type limit: int
        @param start: The index of the first record of the query result
        @type start: int
        @param sort: The column by which to sort the records
        @type sort: str
        @param dir: Direction to sort, either ASC or DESC
        @type dir: str
        @param filters: Values for which to create filters (e.g.,
                        {'device':'^loc.*$', 'severity':[4, 5]})
        @type filters: dict or JSON str representing dict
        @param asof: Last time as of which ranges were accurate
        @type asof: float
        """

    def detail(evid, history=False):
        """
        Get the event detail for an event.

        @param evid: The event ID for which to fetch the detail
        @type evid: str
        @param history: Whether we should look on the history table
        @type history: bool
        """

    def log(evid, message, history=False):
        """
        Add a log message to an event.

        @param evid: The event ID for which to add a log message
        @type evid: str
        @param message: Body of the log message.
        @type message: str
        @param history: Whether we should look on the history table
        @type history: bool
        """

