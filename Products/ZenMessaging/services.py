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

from zope.interface import implements
from Products.ZenMessaging.interfaces import ITriggersService
import zenoss.protocols.protobufs.zep_pb2 as zep
import parser
import httplib
import json
import logging
log = logging.getLogger('zen.triggerservice')

class UrlDispatcher(object):
    
    def __init__(self, **kwargs):
        self.conn = None
        if kwargs:
            self.configure(**kwargs)
        
    def configure(self, **kwargs):
        self.service_host = kwargs.get('host')
        self.service_port = kwargs.get('port')
        self.timeout = kwargs.get('timeout')
        
    def _getConnection(self):
        self.conn = httplib.HTTPConnection(
            self.service_host,
            self.service_port,
            timeout=self.timeout
        )
        return self.conn
        
    def issueRequest(self, url, method="GET", body=None, headers={}):
        log.debug('Making url request for: %s' % url)
        
        if body:
            if not isinstance(body, basestring):
                body = json.dumps(body)
        
        responseString = ""
        try:
            conn = self._getConnection()
            conn.request(
                method,
                url,
                body=body,
                headers=headers
            )
            response = conn.getresponse()
            
            # 204 means request was  ok, but there was no information returned
            if response.status != 200 and \
               response.status != 204:
                raise Exception( "Bad response: %s" % str(response.status) )
            responseString = response.read()
            
        except Exception:
            import traceback
            log.error(traceback.format_exc())

        return responseString
        
    def __del__(self):
        try:
            if self.conn:
                self.conn.close()
        except Exception:
            # already closed
            pass


class TriggersService(object):
    """
    POST    to      /triggers will add,
    POST    to      /triggers/{uuid} will update
    DELETE  from    /triggers/{uuid} will delete, 
    GET     from    /triggers/{uuid} will return trigger, 
    """
    implements(ITriggersService)
    
    _DEFAULT_TRIGGERS_HOST = 'localhost'
    _DEFAULT_TRIGGERS_PORT = '8084'
    _DEFAULT_TRIGGERS_TIMEOUT = 60
    _BASE_TRIGGERS_URL = '/api/triggers'
    
    def __init__(self):
        self._dispatcher = UrlDispatcher(
            host = self._DEFAULT_TRIGGERS_HOST,
            port = self._DEFAULT_TRIGGERS_PORT,
            timeout = self._DEFAULT_TRIGGERS_TIMEOUT,
        )
    
    def _get_url(self, part=None):
        if part:
            return '/'.join([self._BASE_TRIGGERS_URL, part])
        else:
            return self._BASE_TRIGGERS_URL
    
    def _request(self, url, method, body=None, headers={}):
        return self._dispatcher.issueRequest(
            url,
            method=method,
            body=body,
            headers=headers,
        )
    
    def getTriggers(self):
        """
        @return The trigger set with 0 or more triggers.
        @rtype zenoss.protocols.protobufs.zep_pb2.EventTriggerSet
        """
        response = self._request(
            self._get_url(),
            'GET',
            headers={
                'Accept': 'application/x-protobuf'
            }
        )
        trigger_set = zep.EventTriggerSet()
        trigger_set.ParseFromString(response)
        return trigger_set
    
    def addTrigger(self, trigger):
        """
        @param trigger: The trigger to create.
        @type trigger: zenoss.protocols.protobufs.zep_pb2.EventTrigger
        """
        return self._request(
            self._get_url(),
            'POST',
            body = trigger.SerializeToString(),
            headers = {
                'Content-Type': 'application/x-protobuf', 
                'X-Protobuf-FullName': trigger.DESCRIPTOR.full_name,
            }
        )
    
    def removeTrigger(self, trigger):
        """
        @param trigger: The trigger to remove.
        @type trigger: zenoss.protocols.protobufs.zep_pb2.EventTrigger
        """
        return self._request(
            self._get_url(trigger.uuid),
            'DELETE',
        )
    
    def getTrigger(self, uuid):
        """
        @param uuid: The uuid of the trigger to get.
        @type uuid: string
        @return basic python object (not the protobuf)
        """
        response = self._request(
            self._get_url(uuid),
            'GET'
        )
        trigger = zep.EventTrigger()
        trigger.ParseFromString(response)
        return trigger
    
    def updateTrigger(self, trigger):
        """
        @param trigger: The trigger to update.
        @type trigger: zenoss.protocols.protobufs.zep_pb2.EventTrigger
        """
        return self._request(
            self._get_url(trigger.uuid),
            'POST',
            body = trigger.SerializeToString(),
            headers = {
                'Content-Type': 'application/x-protobuf', 
                'X-Protobuf-FullName': trigger.DESCRIPTOR.full_name,
            }
        )
    
    def parseFilter(self, source):
        """
        Parse a filter to make sure it's sane.
        
        @param source: The python expression to test.
        @type source: string
        @todo: make this not allow nasty python.
        """
        tree = parser.expr(source)
        if parser.isexpr(tree):
            return source
        else:
            raise Exception('Invalid filter expression.')
            