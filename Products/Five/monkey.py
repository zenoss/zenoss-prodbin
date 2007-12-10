##############################################################################
#
# Copyright (c) 2004, 2005 Zope Corporation and Contributors.
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
"""Bad monkey!

$Id: monkey.py 62379 2005-12-02 20:23:17Z efge $
"""
def monkeyPatch():
    """Trigger all monkey patches needed to make Five work.

    This adjusts Zope 2 classes to make them work with Zope 3.

    Monkey patches are kept to a minimum level.
    """

    from Products.Five import interfaces, i18n
    interfaces.monkey()
    i18n.monkey()
    localsites_monkey()
    skins_monkey()
    zope3_monkey()

def localsites_monkey():
    from Acquisition import aq_inner, aq_parent
    from zope.component.interfaces import IServiceService
    from zope.component.exceptions import ComponentLookupError

    def getLocalServices(context):
        """Returns the service manager that contains `context`.

        If `context` is a local service, returns the service manager
        that contains that service. If `context` is a service manager,
        returns `context`.

        Otherwise, raises ``ComponentLookupError('Services')``

        Basically, this overrides the one in Zope X3 3.0 so that it
        uses acquisition instead of looking up __parent__.  Monkey
        patching Zope 3 sucks, but X3 3.0 leaves us no choice, really.
        Fortunately, this will disappear in Zope 3.2, so we won't wet
        our pants about this now..."""
        # IMPORTANT
        #
        # This is not allowed to use any services to get its job done!

        while not (context is None or
                   IServiceService.providedBy(context)):
            context = getattr(context, '__parent__', aq_parent(aq_inner(context)))
        if context is None:
            raise ComponentLookupError('Services')
        else:
            return context

    from zope.app.component import localservice
    localservice.getLocalServices = getLocalServices

    from zope.event import notify
    from zope.app.publication.interfaces import EndRequestEvent
    def close(self):
        self.other.clear()
        self._held=None
        notify(EndRequestEvent(None, self))

    from ZPublisher.BaseRequest import BaseRequest
    BaseRequest.close = close

def skins_monkey():
    """Monkey HTTPRequest, from Zope > 2.8.4
    """
    def shiftNameToApplication(self):
        """see zope.publisher.interfaces.http.IVirtualHostRequest"""
        # this is needed for ++skin++
    from ZPublisher.HTTPRequest import HTTPRequest
    HTTPRequest.shiftNameToApplication = shiftNameToApplication

def zope3_monkey():
    """Zope 3 monkeys to get some Zope 3.2 features.

    - Added ContainerModifiedEvent.

    - Added `original` parameter to ObjectCopiedEvent.
    """
    import warnings
    from zope.event import notify
    from zope.interface import implements
    from zope.app.event.objectevent import ObjectModifiedEvent
    from zope.app.event.objectevent import ObjectCopiedEvent
    from zope.app.event.interfaces import IObjectModifiedEvent

    class IContainerModifiedEvent(IObjectModifiedEvent):
        """The container has been modified.

        This event is specific to "containerness" modifications, which
        means addition, removal or reordering of sub-objects.
        """

    class ContainerModifiedEvent(ObjectModifiedEvent):
        """The container has been modified."""
        implements(IContainerModifiedEvent)

    def notifyContainerModified(object, *descriptions):
        """Notify that the container was modified."""
        notify(ContainerModifiedEvent(object, *descriptions))

    def ObjectCopiedEvent_init(self, object, original=None):
        super(ObjectCopiedEvent, self).__init__(object)
        self.original = original
        # BBB goes away in 3.3
        if original is None:
            warnings.warn(
                "%s with no original is deprecated and will no-longer "
                "be supported starting in Zope 3.3."
                % self.__class__.__name__,
                DeprecationWarning, stacklevel=2)

    from zope.app.container import contained
    from zope.app.container import interfaces
    interfaces.IContainerModifiedEvent = IContainerModifiedEvent
    contained.ContainerModifiedEvent = ContainerModifiedEvent
    contained.notifyContainerModified = notifyContainerModified
    ObjectCopiedEvent.__init__ = ObjectCopiedEvent_init
