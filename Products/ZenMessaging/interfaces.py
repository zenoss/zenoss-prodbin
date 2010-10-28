###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from zope.interface import Interface

class ITriggersService(Interface):
    """
    Provides the API to the remote ZEP service for triggers.
    """
    def getTriggers():
        """
        Get all triggers without regard to user, group or role.
        
        @return The set of all triggers.
        @rtype: protobuf EventTriggerSet
        """

    def addTrigger(trigger):
        """
        @param trigger: the trigger protobuf to add.
        @type trigger: EventTrigger
        """

    def removeTrigger(trigger):
        """
        @param trigger:the trigger to be removed
        @type trigger: EventTrigger
        """

    def getTrigger(uuid):
        """
        @param uuid the uuid of the trigger to retrieve
        """
        
    def updateTrigger(trigger):
        """
        @param trigger: the trigger to be updated
        @type trigger: protobuf EventTrigger
        """
        
    def parseFilter(source):
        """
        @param source the filter source to be parsed
        """

class IProtobufJsonizable(Interface):
    """
    Interface for converting a protobuf into a jsonizable object and recreating
    the same protobuf from the jsonizable object.
    
    The following example should be true:
    
        # get a protobuf and set some properties on it. Note the nested
        # proto message of prop3 and the repeated property of prop4.
        my_proto = MyProto()
        my_proto.prop1 = 'foo'
        my_proto.prop2 = 'bar'
        my_proto.prop3.something = 'gorilla'
        my_proto.prop3.another = 'monkey'
        baz = my_proto.prop4.add()
        baz.banana = True
        baz.count = 836794
        baz2 = my_proto.prop4.add()
        baz2.banana = False
        
        # get `my_proto` as a jsonizable object
        my_jsonizable_obj = IProtobufJsonizable(my_proto).json_friendly()
        
        my_other_proto = MyProto()
        IProtobufJsonizable(my_other_proto).fill(my_jsonizable_obj)
        
        # the following will be true:
        my_other_proto == my_proto
    
    """
    
    def fill(jsonizable):
        """
        Given a jsonizable object, use it to recreate a protobuf.
        """
    
    def json_friendly():
        """
        Return a jsonizable structure of this protobuf. This jsonizable structure
        should be able to be fed into fill() and recreate an identicle protobuf.
        
        @return jsonizable object.
        @rtype primitive python object(s) (dictionary, list, etc.).
        """
