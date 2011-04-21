###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import inspect
import logging
from Products.ZenUtils.jsonutils import json, unjson
import transaction
from uuid import uuid4

log = logging.getLogger('extdirect')

class DirectException(Exception):
    pass



class DirectResponse(object):
    """
    Encapsulation of the simple protocol used to send results and messages to
    the front end.
    """
    _data = None
    def __init__(self, msg=None, success=True, **kwargs):
        self._data = {}
        self._data.update(kwargs)
        self._data['success'] = success
        if msg:
            self._data['msg'] = msg

    @property
    def data(self):
        return self._data

    def __setitem__(self, key, value):
        self._data[key] = value

    @staticmethod
    def exception(exception, **kwargs):
        msg = exception.__class__.__name__ + ': ' + str(exception)
        return DirectResponse(msg, success=False, type='exception', **kwargs)

    @staticmethod
    def fail(msg=None, **kwargs):
        return DirectResponse(msg, success=False, type='error', **kwargs)

    @staticmethod
    def succeed(msg=None, **kwargs):
        return DirectResponse(msg, success=True, **kwargs)

    def __json__(self):
        return self.data

class DirectMethodResponse(object):
    """
    Encapsulation of the response of a method call for Ext Direct.
    """
    def __init__(self, tid, action, method, uuid):
        self.tid = tid
        self.type = 'rpc'
        self.action = action
        self.method = method
        self.uuid = uuid
        self.result = None

    def __json__(self):
        return {
            'tid': self.tid,
            'type' : self.type,
            'action': self.action,
            'method': self.method,
            'uuid': self.uuid,
            'result': self.result
        }

class DirectRouter(object):
    """
    Basic Ext.Direct router class.

    Ext.Direct allows one to create an API that communicates with a single URL,
    which then routes requests to the appropriate method. The client-side API
    object matches the server-side API object.

    This base class parses an Ext.Direct request, which contains the name of
    the method and any data that should be passed, and routes the data to the
    approriate method. It then receives the output of that call and puts it
    into the data structure expected by Ext.Direct.

    Call an instance of this class with the JSON from an Ext.Direct request.
    """

    @json
    def __call__(self, body):
        # Decode the request data
        body = unjson(body)
        self._body = body

        if isinstance(body, list):
            directRequests = body
        elif isinstance(body, dict):
            directRequests = [body]
        else:
            raise DirectException("Body is not a supported type: %s" % body)

        directResponses = []
        for directRequest in directRequests:
            directResponses.append(self._processDirectRequest(directRequest))

        if len(directResponses) == 1:
            directResponses = directResponses[0]

        return directResponses

    def _processDirectRequest(self, directRequest):
        # Add a UUID so we can track it in the logs
        uuid = str(uuid4())

        # Double-check that this request is meant for this class
        action = directRequest.get('action')
        clsname = self.__class__.__name__
        if action != clsname:
            raise DirectException(("Action specified in request ('%s') is"
                                  " not named %s.") % (action, clsname))

        # Pull out the method name and make sure it exists on this class
        method = directRequest.get('method')
        if not method:
            raise DirectException("No method specified. Is this a valid"
                                  " Ext.Direct request?")
        try:
            _targetfn = getattr(self, method)
        except AttributeError:
            raise DirectException("'%s' is not the name of a method on %s" % (
                method, clsname
            ))

        # Pull out any arguments. Sent as an array containing a hash map, so
        # get the first member.
        data = directRequest.get('data')
        if not data:
            data = {}
        else:
            data = data[0]

        if isinstance(data, (int, basestring)):
            data = {'id': data}

        # Cast all keys as strings, in case of encoding or other wrinkles
        data = dict((str(k), v) for k,v in data.iteritems())
        self._data = data
        response = DirectMethodResponse(tid=directRequest['tid'], method=method, action=action, uuid=uuid)

        # Finally, call the target method, passing in the data
        try:
            response.result = _targetfn(**data)
        except Exception as e:
            log.error('DirectRouter suppressed the following exception (Response %s):' % response.uuid)
            log.exception(e)
            # rollback ZODB transaction on uncaught exceptions
            transaction.abort()
            response.result = DirectResponse.exception(e)

        return response


class DirectProviderDefinition(object):
    """
    Turns a L{DirectRouter} subclass into JavaScript object representing the
    config of the client-side API.

    Inspects the given subclass and retrieves the names of all public methods,
    then defines those as actions on the Ext.Direct provider, and creates the
    JS that adds the provider.

    See http://extjs.com/products/extjs/direct.php for a full explanation of
    protocols and features of Ext.Direct.
    """
    def __init__(self, routercls, url, timeout, ns=None):
        """
        @param routercls: A L{DirectRouter} subclass
        @type routercls: class
        @param url: The url at which C{routercls} is available
        @type url: str
        @param ns: The client-side namespace in which the provider should live.
                   The provider will be available at [ns].[routercls.__name__].
                   For example, if ns is 'Zenoss.remote' and routercls is named
                   'EventConsole', client-side code would call
                   C{Zenoss.remote.EventConsole.my_method(params, callback)}.
        """
        self.routercls = routercls
        self.url = url
        self.ns = ns
        self.timeout = timeout

    def _config(self):
        actions = []
        for name, value in inspect.getmembers(self.routercls):
            if name.startswith("_"):
                continue
            if inspect.ismethod(value):

                ## Update this when extdirect doesn't freak out when you specify
                ## actual lens (we're passing them all in as a single dict, so
                ## from the perspective of Ext.Direct they are all len 1)
                #args = inspect.getargspec(value)[0]
                #args.remove('self')
                #arglen = len(args)
                arglen = 1

                actions.append({'name':name, 'len':arglen})
        config = {
            'id': self.routercls.__name__,
            'type': 'remoting',
            'url': self.url,
            'timeout': self.timeout,
            'enableBuffer': 100,
            'actions': {
                self.routercls.__name__: actions
            }
        }
        if self.ns:
            config['namespace'] = self.ns
        return config

    def render(self):
        """
        Generate and return an Ext.Direct provider definition, wrapped in a
        <script> tag and ready for inclusion in an HTML document.
        """
        config = self._config()
        source = "\nExt.Direct.addProvider(%s);\n" % json(config)
        return source.strip()

