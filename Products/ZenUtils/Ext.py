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
from Products.ZenUtils.extdirect.zope.router import ZopeDirectRouter
from Products.ZenUI3.utils.javascript import JavaScriptSnippet


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


class DirectRouter(ZopeDirectRouter):
    _asof = None

    def _set_asof(self, asof):
        self._asof = asof

    def __call__(self):
        result = unjson(super(DirectRouter, self).__call__())
        return json(result)

