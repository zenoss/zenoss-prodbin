#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

"""SiteScopeExcept

SiteScope Exception Classes

$Id: SiteScopeExcept.py,v 1.3 2002/06/20 17:44:04 alex Exp $"""

__version__ = "$Revision: 1.3 $"[11:-2]

import zLOG
from App.Dialogs import MessageDialog

class CMException(Exception): pass


class ParseError(CMException):
    def __init__(self, url):
        self._url = url


    def dialog(self):
        '''Returns a MessageDialog object as output
        from a ParseError exception and logs to
        syslog using zLOG'''

        zLOG.LOG(
            "SiteScopeParser",
            100,
            "Parse failure",
            "Document %s failed to parse" % self._url,
            0)

        return MessageDialog(
            title="SiteScopeParser ParseError",
            message="Inconsistent data resulted from parsing %s" % self._url,
            action='manage_editParserForm')


class AuthError(CMException):
    def __init__(self, user):
        self._user = user


    def dialog(self):
        '''Returns a MessageDialog object as output
        from an AuthError exception and logs to
        syslog using zLOG'''

        zLOG.LOG(
            "SiteScopeParser",
            100,
            "Authentication failure",
            "User %s failed authentication" % self._user,
            0)

        return MessageDialog(
            title="SiteScopeParser AuthError",
            message="Authentication for user %s failed" % self._user, 
            action='manage_editParserForm')


class HostError(CMException):
    def __init__(self, host):
        self._host = host


    def dialog(self):
        '''Returns a MessageDialog object as output
        from a HostError exception and logs to
        syslog using zLOG'''

        zLOG.LOG(
            "SiteScopeParser",
            100,
            "Connection Failure",
            "Couldn't connect to host %s" % self._host,
            0)

        return MessageDialog(
            title="SiteScopeParser HostError",
            message="Host not found for %s" % self._host,
            action='manage_editParserForm')


class LocationError(CMException):
    def __init__(self, url):
        self._url = url


    def dialog(self):
        '''Returns a MessageDialog object as output
        from a LocationError exception and logs to
        syslog using zLOG'''

        zLOG.LOG(
            "SiteScopeParser",
            100,
            "URL couldn't be found",
            "Could not retrieve URL %s" % self._url,
            0)

        return MessageDialog(
            title="SiteScopeParser LocationError",
            message="URL not found: %s" % self._url,
            action='manage_editParserForm')

class UrlFormatError(Exception):

    def dialog(self):
        '''Returns a MessageDialog object as output
        from a NoHTTPError exception and logs to
        syslog using zLOG... caused by omitting
        the protocol:// field of a URL'''

        zLOG.LOG(
            "SiteScopeParser",
            100,
            "User forgot protocol://",
            "You must include the protocol:// field",
            0)

        return MessageDialog(
            title="SiteScopeParser NoHTTPError",
            message="You must supply a protocol:// field",
            action='addParserForm')
