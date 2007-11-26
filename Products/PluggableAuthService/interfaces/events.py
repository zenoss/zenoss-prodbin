from zope.interface import Attribute, Interface

class IPASEvent(Interface):
    """An event related to a PAS principal.
    """

    principal = Attribute("The subject of the event.")


class IPrincipalCreatedEvent(IPASEvent):
    """A new principal has been created.
    """


class IUserLoggedInEvent(IPASEvent):
    """ A user logged in.
    """


class IUserLoggedOutEvent(IPASEvent):
    """ A user logged out.
    """


class IPrincipalDeletedEvent(IPASEvent):
    """A user has been removed.
    """


class ICredentialsUpdatedEvent(IPASEvent):
    """A principal has changed her password.

    Sending this event will cause a PAS user folder to trigger its active
    credential update plugins.
    """
    password = Attribute('The new password')


class IPropertiesUpdatedEvent(IPASEvent):
    """A principals properties have been updated.
    """
    properties = Attribute('List of modified property ids')


