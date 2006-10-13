##############################################################################
#
# Copyright (c) 2005 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Local sites

$Id: localsite.py 60972 2005-10-30 16:03:43Z philikon $
"""
from zope.event import notify
from zope.interface import directlyProvides, directlyProvidedBy
from zope.interface import implements
from zope.component import getGlobalServices
from zope.component.exceptions import ComponentLookupError
from zope.component.servicenames import Utilities

from zope.app.site.interfaces import ISite, IPossibleSite
from zope.app.component.localservice import getNextServices, getNextService
from zope.app.publication.zopepublication import BeforeTraverseEvent

from ExtensionClass import Base
from Acquisition import aq_base, aq_inner, aq_parent
from Products.SiteAccess.AccessRule import AccessRule
from ZPublisher.BeforeTraverse import registerBeforeTraverse
from ZPublisher.BeforeTraverse import unregisterBeforeTraverse

from Products.Five.site.interfaces import IFiveSiteManager, IFiveUtilityService

def serviceServiceAdapter(ob):
    """An adapter * -> IServiceService.

    This is registered in place of the one in Zope 3 so that we lookup
    using acquisition instead of ILocation.
    """
    current = ob
    while True:
        if ISite.providedBy(current):
            return current.getSiteManager()
        current = getattr(current, '__parent__', aq_parent(aq_inner(current)))
        if current is None:
            raise ComponentLookupError("Could not adapt %r to"
                                       " IServiceService" % (ob, ))

HOOK_NAME = '__local_site_hook__'

class LocalSiteHook(Base):
    def __call__(self, container, request):
        notify(BeforeTraverseEvent(container, request))


def enableLocalSiteHook(obj):
    """Install __before_traverse__ hook for Local Site
    """
    # We want the original object, not stuff in between, and no acquisition
    obj = aq_base(obj)
    if not IPossibleSite.providedBy(obj):
        raise TypeError, 'Must provide IPossibleSite'
    hook = AccessRule(HOOK_NAME)
    registerBeforeTraverse(obj, hook, HOOK_NAME, 1)

    if not hasattr(obj, HOOK_NAME):
        setattr(obj, HOOK_NAME, LocalSiteHook())

    directlyProvides(obj, ISite, directlyProvidedBy(obj))

def disableLocalSiteHook(obj):
    """Remove __before_traverse__ hook for Local Site
    """
    # We want the original object, not stuff in between, and no acquisition
    obj = aq_base(obj)
    if not ISite.providedBy(obj):
        raise TypeError, 'Must provide ISite'
    unregisterBeforeTraverse(obj, HOOK_NAME)
    if hasattr(obj, HOOK_NAME):
        delattr(obj, HOOK_NAME)

    directlyProvides(obj, directlyProvidedBy(obj) - ISite)

class FiveSiteManager(object):
    implements(IFiveSiteManager)

    def __init__(self, context):
        # make {get|query}NextServices() work without having to
        # resort to Zope 2 acquisition
        self.context = self.__parent__ = context

    def next(self):
        obj = self.context
        while obj is not None:
            obj = aq_parent(aq_inner(obj))
            if ISite.providedBy(obj):
                return obj.getSiteManager()
        # only with Zope X3 3.0 always return something else than None
        # in Zope 3.1+, returning None means global site manager will
        # be used
        return getGlobalServices()
    next = property(next)

    def getServiceDefinitions(self):
        """Retrieve all Service Definitions

        Should return a list of tuples (name, interface)
        """
        return getNextServices(self).getServiceDefinitions()

    def getInterfaceFor(self, service_type):
        """Retrieve the service interface for the given name
        """
        for type, interface in self.getServiceDefinitions():
            if type == service_type:
                return interface

        raise NameError(service_type)

    def getService(self, name):
        """Retrieve a service implementation

        Raises ComponentLookupError if the service can't be found.
        """
        if name == Utilities:
            return IFiveUtilityService(self.context)
        return getNextService(self, name)

    def registerUtility(self, interface, utility, name=''):
        """See Products.Five.site.interfaces.IRegisterUtilitySimply"""
        return IFiveUtilityService(self.context).registerUtility(
            interface, utility, name)

class FiveSite:
    implements(IPossibleSite)

    def getSiteManager(self):
        return FiveSiteManager(self)

    def setSiteManager(self, sm):
        raise NotImplementedError('This class has a fixed site manager')
