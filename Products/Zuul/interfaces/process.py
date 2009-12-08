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
from tree import ITreeNode
from info import IInfo


class IProcessEntity(Interface):
    """
    Marker interface for OSProcessClass and OSProcessOrganizer
    """

class IProcessNode(ITreeNode):
    """
    Marker interface for a node in a process tree.
    """

class IProcessInfo(IInfo):
    """
    Represents a single ProcessClass instance.
    """
    name = Attribute('The name of the process')
    description = Attribute('A description of the process')
    isMonitoringAcquired = Attribute('Does this process acquire its monitor '
                                     'eventSeverity properties from container')
    monitor = Attribute('Whether or not the process is monitored')
    eventSeverity = Attribute('The severity of the event fired when this '
                             'process goes down')
    hasRegex = Attribute('OSProcessClasses have regexes, OSProcessOrganizers'
                         ' do not')
    regex = Attribute('Regular expression used to match process to a running '
                      'command on the managed host')
    ignoreParameters = Attribute('Only match the regex to the command not its'
                                 ' parameters')

class IProcessFacade(Interface):

    def getInfo(id):
        """
        Get information about the OSProcessOrganizer and OSProcessClass
        identified by id.
        """

    def getDevices(id):
        """
        Get the devices with OSProcess instances that fall under the
        IProcessEntity identified by the id parameter.
        """

    def getEvents(id):
        """
        Get the events associated with OSProcess instances that fall under the
        IProcessEntity identified by the id parameter.
        """
