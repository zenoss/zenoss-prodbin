from Acquisition import aq_parent
from zope.component import adapter
from zope.component import subscribers
from zope.interface import implements
from Products.PluggableAuthService.interfaces.events import *
from Products.PluggableAuthService.interfaces.authservice import IBasicUser

class PASEvent(object):
    implements(IPASEvent)

    def __init__(self, principal):
        self.principal=principal
        self.object=principal


class PrincipalCreated(PASEvent):
    implements(IPrincipalCreatedEvent)


class PrincipalDeleted(PASEvent):
    implements(IPrincipalDeletedEvent)


class CredentialsUpdated(PASEvent):
    implements(ICredentialsUpdatedEvent)

    def __init__(self, principal, password):
        super(CredentialsUpdated, self).__init__(principal)
        self.password=password


class PropertiesUpdated(PASEvent):
    implements(IPropertiesUpdatedEvent)

    def __init__(self, principal, properties):
        super(CredentialsUpdated, self).__init__(principal)
        self.properties=properties


@adapter(IBasicUser, ICredentialsUpdatedEvent)
def userCredentialsUpdatedHandler(principal, event):
    pas = aq_parent(principal)
    pas.updateCredentials(
            pas,
            pas.REQUEST,
            pas.REQUEST.RESPONSE,
            principal.getId(),
            event.password)


@adapter(IPASEvent)
def PASEventNotify(event):
    """Event subscriber to dispatch PASEvent to interested adapters."""
    adapters = subscribers((event.principal, event), None)
    for adapter in adapters:
        pass # getting them does the work

