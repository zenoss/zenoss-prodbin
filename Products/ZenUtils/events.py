##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.PluggableAuthService.interfaces.events import IUserLoggedInEvent
from Products.PluggableAuthService.interfaces.events import IUserLoggedOutEvent
from Products.PluggableAuthService.events import PASEvent
from zope.interface import implements, Interface, Attribute
from zope.event import notify
from ZODB.transact import transact

class UserLoggedInEvent(PASEvent):
    """
    Login notification event.

    Subscribe to this to run code when a user logs in.
    The username can be obtained in the handler via: evt.object.id

    WARNING: Currently it doesn't notify when switching directly from
             a non-admin user to the admin user without logging out,
             because we're unable to determine whether the login succeeded.
    """
    implements(IUserLoggedInEvent)


class UserLoggedOutEvent(PASEvent):
    """
    Manual logout notification event.

    This does not fire for session timeouts.
    """
    implements(IUserLoggedOutEvent)

class IZopeApplicationOpenedEvent(Interface):
    """
    Returns the Zope application.
    """
    app = Attribute("The Zope Application")

class ZopeApplicationOpenedEvent(object):
    implements(IZopeApplicationOpenedEvent)

    def __init__(self, app):
        self.app = app

def notifyZopeApplicationOpenedSubscribers(event):
    """
    Re-fires the IDatabaseOpenedWithRoot notification to subscribers with an
    open handle to the application defined in the database.
    """
    db = event.database
    conn = db.open()
    try:
        app = conn.root()['Application']
        transact(notify)(ZopeApplicationOpenedEvent(app))
    finally:
        conn.close()
