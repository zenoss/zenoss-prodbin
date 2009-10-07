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

# Functions to simplify form submission return values.

import transaction

from Products.ZenUtils.json import json, unjson
from Products.ZenUI3.utils.javascript import JavaScriptSnippet
from Products.Five.browser import BrowserView


class FormResponse(object):
    """
    Builds a response for an Ext form.
    """
    _errors = None
    _redirect = None

    def has_errors(self):
        return bool(self._errors)

    def redirect(self, url):
        self._redirect = url

    def error(self, field_name, error_text):
        if self._errors is None:
            self._errors = {}
        self._errors[field_name] = error_text

    @json
    def get_response(self):
        return {
            'success':  not self.has_errors(),
            'redirect': self._redirect,
            'errors':   self._errors or {}
        }


def form_action(f):
    """
    Decorator for methods that are the targets of Ext form submission.

    Provides transaction rollback, so methods can be used as their own
    validation without harm.
    """
    def inner(*args, **kwargs):
        savepoint = transaction.savepoint()
        result = f(*args, **kwargs)
        if isinstance(result, FormResponse):
            if result.has_errors():
                savepoint.rollback()
            return result.get_response()
        return result
    return inner


class DirectRouter(BrowserView):
    """
    Base class for Ext.Direct routers.

    Ext.Direct allows one to create an API that communicates with a single URL,
    which then routes requests to the appropriate method. The client-side API
    object matches the server-side API object.

    This base class parses an Ext.Direct request, which contains the name of
    the method and any data that should be passed, and routes the data to the
    approriate method. It then receives the output of that call and puts it
    into the data structure expected by Ext.Direct.

    @rtype JSON
    """
    _asof = None

    def _set_asof(self, asof):
        self._asof = asof

    def __call__(self):
        body = self.request.get('BODY')
        self.data = unjson(body)
        method = self.data['method']
        data = self.data['data']
        if 'asof' in self.data:
            self._set_asof(self.data['asof'])
        if not data:
            data = {}
        else:
            data = data[0]

        # Cast all keys as strings in case of unicode problems
        data = dict((str(k), v) for k,v in data.items())

        # Call the specified method
        result = getattr(self, method)(**data)

        self.request.response.setHeader('Content-Type', 'application/json')
        return json({
            'type':'rpc',
            'tid': self.data['tid'],
            'action':self.data['action'],
            'method':self.data['method'],
            'result': result,
            'asof': self._asof
        })


class DirectProviderDefinition(JavaScriptSnippet):
    """
    Turns a L{DirectRouter} subclass into JavaScript object representing the
    config of the client-side API.

    Inspects the given subclass and retrieves the names of all public methods,
    then defines those as actions on the Ext.Direct provider, and creates the
    JS that adds the provider.

    As this is a JavaScriptSnippet, the resulting code will be included in the
    rendered template if the snippet is registered as a viewlet in ZCML and the
    appropriate provider is referenced in the template.

    See http://extjs.com/products/extjs/direct.php for a full explanation of
    protocols and features of Ext.Direct.
    """
    _router = None
    _url = None
    def snippet(self):
        attrs = [a for a in self._router.__dict__.keys() if not a.startswith('_')]
        methodtpl = '{name:"%s", len:1}'
        methods = ",".join([methodtpl % a for a in attrs])
        return """
        Ext.onReady(function(){
            Ext.Direct.addProvider(
                  {
                      type: 'remoting',
                      url: '%(url)s',
                      actions: {
                          "%(clsname)s":[
                            %(methods)s
                          ]
                      },
                      namespace: 'Zenoss.remote'
                  }
              );
        });
        """ % dict(url=self._url, clsname=self._router.__name__, methods=methods)
